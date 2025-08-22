from app import app, db
from app.models import User
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import LoginForm, RegistrationForm
import io


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('Your account is not registered. Contact Administrator.')
        elif user.activation_key != "" :
            flash('Your account is not activated. Contact Administrator for activation key.', 'danger')
        elif user.locked:
            flash('Your account is locked. Contact Administrator.', 'danger')
        else:
            if user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')

                if next_page == None or not next_page.startswith('/'):
                    next_page = url_for('home')
                return redirect(next_page)
            elif user.user_type != "super":
                user.failed_attempt = user.failed_attempt-1
                if user.failed_attempt == 0:
                    user.locked = True
                    flash('Your account is locked. Contact Administrator', 'danger')
                else:
                    flash(f"Incorrect password. {user.failed_attempt} remaining attempt(s).", 'danger')    
                db.session.commit()
            else:
                flash('Incorrect password. Try again.', 'danger')

                
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()

    if request.method == 'POST':
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.email == form.email.data:
            if user.activation_key == form.activation_key.data: 
                user.email = form.email.data
                user.set_password(form.password.data)
                user.locked = False
                user.failed_attempt = 3
                user.activation_key = ""
                db.session.commit()
                flash('Account registration complete.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Incorrect activation key. Contact Administrator', 'danger')
                return render_template('register.html', form=form)
        else:
            flash('This email is not allowed to be registered. Contact Administrator', 'danger')
            return render_template('register.html', form=form)
    return render_template('register.html', form=form)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int("8080"))
