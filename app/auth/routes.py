from flask import render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user
from app.auth import bp
from app.models import User
from app import db
from app.auth.forms import RegistrationForm, LoginForm


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """register new user"""
    form = RegistrationForm()

    # If the request method is POST but the form doesn't validate, print the errors
    if form.is_submitted():
        print("Form was submitted")
        if not form.validate():
            print("Form did not validate")
            print(form.errors)  # This will print the errors to your terminal/console

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now registered!')
        return redirect(url_for('main.index'))

    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """login user"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    """logout user"""
    logout_user()
    return redirect(url_for('main.index'))