from app import app, db
from app.models import User, Employee, Client, Intervention, Invoice
from sqlalchemy import func
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import LoginForm, RegistrationForm
from datetime import date, timedelta, datetime


def get_date_ranges():
    today = date.today()
    # Current Month
    start_month = today.replace(day=1)
    end_month = (start_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    # Last Month
    this_month = today.replace(day=1)
    start_prev_month = (this_month - timedelta(days=1)).replace(day=1)
    end_prev_month = (start_prev_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    # Current Quarter
    quarter = (today.month - 1) // 3 + 1
    start_quarter = date(today.year, 3 * quarter - 2, 1)
    end_quarter = (start_quarter + timedelta(days=92)).replace(day=1) - timedelta(days=1)
    # Last Quarter
    prev_quarter = (today.month - 4) // 3 + 1
    start_prev_quarter = date(today.year, 3 * prev_quarter - 2, 1)
    end_prev_quarter = (start_prev_quarter + timedelta(days=92)).replace(day=1) - timedelta(days=1)
    # Current Year
    start_year = date(today.year, 1, 1)
    end_year = date(today.year, 12, 31)
    # Last Year
    start_prev_year = date(today.year - 1, 1, 1)
    end_prev_year = date(today.year - 1, 12, 31)

    return {
        'month': (start_month, end_month),
        'quarter': (start_quarter, end_quarter),
        'year': (start_year, end_year),
        'last month': (start_prev_month, end_prev_month),
        'last quarter': (start_prev_quarter, end_prev_quarter),
        'last year': (start_prev_year, end_prev_year)
    }


def get_totals():
    ranges = get_date_ranges()
    results = {}
    for period, (start, end) in ranges.items():
        total_invoiced = db.session.query(func.sum(Invoice.total_cost))\
            .filter(Invoice.invoiced_date.between(start, end))\
            .scalar() or 0.0

        total_received = db.session.query(func.sum(Invoice.total_cost))\
            .filter(Invoice.invoiced_date.between(start, end))\
            .filter(Invoice.status == 'Paid')\
            .scalar() or 0.0

        results[period] = {
            'total_invoiced': total_invoiced,
            'total_received': total_received
        }
    return results


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/home')
def home():
    if current_user.is_authenticated:
        total_employees = Employee.query.count()
        total_clients = Client.query.count()
        total_interventions = Intervention.query.count()
        user_interventions = Intervention.query.join(Employee).filter(Employee.email == current_user.email).count()
        totals = get_totals()
        return render_template('home.html', total_employees=total_employees, total_clients=total_clients, user_interventions=user_interventions, total_interventions=total_interventions, totals=totals)
    return render_template('home.html')

# @app.route('/admin')
# def admin():
#     return render_template('admin.html')


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
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if not user:
            flash('Your account is not registered. Contact Administrator.')
        
        if user.user_type == "super":
            if user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                if next_page == None or not next_page.startswith('/'):
                    next_page = url_for('home')
                return redirect(next_page)
            else:
                flash('Incorrect password! Try again.', 'danger')

        if user.activation_key != "" :
            flash('Your account is not activated. Contact Administrator for activation key.', 'danger')

        if user.locked_until and datetime.now() < user.locked_until:
            remaining_time = user.locked_until - datetime.now()
            rem_min = int(remaining_time.total_seconds() / 60)
            rem_sec = int(remaining_time.total_seconds() % 60)
            flash(f"You account is locked for another {rem_min}m and {rem_sec}s.", 'danger')
            return render_template('login.html', form=form)

        if user.check_password(form.password.data):
            user.failed_attempt = 3
            user.failed_until = None
            db.session.commit()
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            if next_page == None or not next_page.startswith('/'):
                next_page = url_for('home')
            return redirect(next_page)
        else:
            user.failed_attempt = user.failed_attempt-1
            if user.failed_attempt <= 0:
                user.locked_until = datetime.now() + timedelta(minutes=15)
                flash('Your account is locked for next 15 minutes. Contact Administrator for password reset.', 'danger')
            else:
                flash(f"Incorrect password! {user.failed_attempt} remaining attempt(s).", 'danger')
            db.session.commit()

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
                user.locked_until = None
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
