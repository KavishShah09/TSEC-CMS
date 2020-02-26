from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, SelectField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('config.py')

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


class SignUpForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=100)])
    email = StringField('Email', [validators.Length(min=6, max=100)])
    year = SelectField('Year', choices=[
                       ('F.E.', 'F.E.'), ('S.E.', 'S.E.'), ('T.E.', 'T.E.'), ('B.E.', 'B.E.')])
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        year = form.year.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name , email, year, username, password, role) VALUES(%s, %s, %s, %s, %s, %s)",
                    (name, email, year, username, password, 'user'))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('signUp.html', form=form)


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=100)])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password_input = form.password.data

        cur = mysql.connection.cursor()

        result = cur.execute(
            "SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']
            role = data['role']

            if sha256_crypt.verify(password_input, password):
                session['logged_in'] = True
                session['username'] = username
                session['role'] = role
                flash('You are now logged in', 'success')
                if role == 'admin':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('add_complaint'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', form=form, error=error)

            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', form=form, error=error)

    return render_template('login.html', form=form)


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login', 'info')
            return redirect(url_for('login'))
    return wrap


def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['role'] == 'admin':
            return f(*args, **kwargs)
        else:
            flash('You are not an admin', 'danger')
            return redirect(url_for('add_complaint'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
@is_admin
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM complaints;")
    complaints = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', complaints=complaints)
    else:
        msg = 'No complaints have been registered'
        return render_template('dashboard.html', msg=msg)


@app.route('/dashboard/<string:id>/')
def complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM complaints WHERE id=%s", [id])
    complaint = cur.fetchone()
    return render_template('complaint.html', complaint=complaint)


class ComplaintForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=20)])


@app.route('/add_complaint', methods=['GET', 'POST'])
@is_logged_in
def add_complaint():
    form = ComplaintForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO complaints(title, body, author) VALUES(%s, %s, %s)",
                    (title, body, session['username']))

        mysql.connection.commit()
        cur.close()

        flash('Your complaint has been registered', 'success')
        if session['role'] == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('add_complaint'))

    return render_template('add_complaint.html', form=form)


@app.route('/status_complaint/<string:id>', methods=['POST'])
@is_logged_in
def status_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM complaints WHERE id=%s", [id])
    complaint = cur.fetchone()
    status = complaint['status']
    if status == 'Open':
        status = 'Closed'
        cur.execute(
            "UPDATE complaints SET status = %s WHERE id=%s", [status, id])
    else:
        status = 'Open'
        cur.execute(
            "UPDATE complaints SET status = %s WHERE id=%s", [status, id])

    mysql.connection.commit()
    cur.close()

    flash('Status has been changed', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete_complaint/<string:id>', methods=['POST'])
@is_logged_in
def delete_complaint(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM complaints WHERE id=%s", [id])

    mysql.connection.commit()
    cur.close()

    flash('Complaint has been deleted', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
