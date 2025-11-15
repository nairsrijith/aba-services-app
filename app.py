from app import app, db
from app.models import Employee, Client, Intervention, Invoice, PayStub, PayStubItem
from sqlalchemy import func, case, and_
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import LoginForm, RegistrationForm
from datetime import date, timedelta, datetime, time
from sqlalchemy import and_, extract
import os

from gevent.pywsgi import WSGIServer


org_name = os.environ.get('ORG_NAME', 'My Organization')


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
        'last month': (start_prev_month, end_prev_month),
        'quarter': (start_quarter, end_quarter),
        'last quarter': (start_prev_quarter, end_prev_quarter),
        'year': (start_year, end_year),
        'last year': (start_prev_year, end_prev_year)
    }


def get_session_stats(employee_email=None):
    today = date.today()
    
    # Calculate date ranges
    # Current week (Monday to Sunday)
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    
    # Current month
    current_month_start = today.replace(day=1)
    next_month = today.replace(day=28) + timedelta(days=4)
    current_month_end = next_month - timedelta(days=next_month.day)
    
    # Year to date
    year_start = today.replace(month=1, day=1)
    
    # Last week
    last_week_start = current_week_start - timedelta(days=7)
    last_week_end = current_week_start - timedelta(days=1)
    
    # Last month
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    
    # Last year
    last_year_start = date(today.year - 1, 1, 1)
    last_year_end = date(today.year - 1, 12, 31)
    
    # Base query
    query = db.session.query(
        func.count(Intervention.id).label('session_count'),
        func.sum(Intervention._duration).label('total_hours')  # Use the actual column name
    ).select_from(Intervention)
    
    if employee_email:
        query = query.join(Employee).filter(Employee.email == employee_email)
    
    # Function to get stats for a date range
    def get_stats_for_range(start_date, end_date):
        result = query.filter(Intervention.date.between(start_date, end_date)).first()
        return {
            'sessions': result.session_count or 0,
            'hours': float(result.total_hours or 0)
        }
    
    return {
        'current_week': get_stats_for_range(current_week_start, current_week_end),
        'current_month': get_stats_for_range(current_month_start, current_month_end),
        'year_to_date': get_stats_for_range(year_start, today),
        'last_week': get_stats_for_range(last_week_start, last_week_end),
        'last_month': get_stats_for_range(last_month_start, last_month_end),
        'last_year': get_stats_for_range(last_year_start, last_year_end)
    }


def get_monthly_totals():
    today = date.today()
    start_date = date(today.year - 1, today.month, 1)  # 12 months ago
    
    # Subquery to get the total duration per invoice
    total_duration_per_invoice = db.session.query(
        Intervention.invoice_number,
        func.sum(Intervention._duration).label('total_duration')
    ).filter(Intervention.invoiced == True)\
     .group_by(Intervention.invoice_number)\
     .subquery()

    # Get monthly data for the past 12 months based on intervention dates with prorated invoice amounts
    monthly_data = db.session.query(
        func.date_trunc('month', Intervention.date).label('month'),
        func.sum(
            case(
                (Intervention.invoiced == True,
                 (Intervention._duration / total_duration_per_invoice.c.total_duration) * Invoice.total_cost)
            , else_=0)
        ).label('total_invoiced'),
        func.sum(
            case(
                (and_(Intervention.invoiced == True, Invoice.status == 'Paid'),
                 (Intervention._duration / total_duration_per_invoice.c.total_duration) * Invoice.total_cost)
            , else_=0)
        ).label('total_received')
    ).join(Invoice, Intervention.invoice_number == Invoice.invoice_number)\
     .join(total_duration_per_invoice, Intervention.invoice_number == total_duration_per_invoice.c.invoice_number)\
     .filter(Intervention.date >= start_date)\
     .group_by('month')\
     .order_by('month').all()
    
    # Get monthly paystub totals based on intervention dates
    monthly_paystubs = db.session.query(
        func.date_trunc('month', Intervention.date).label('month'),
        func.sum(PayStubItem.amount).label('total_amount')
    ).join(PayStubItem, Intervention.id == PayStubItem.intervention_id)\
     .filter(Intervention.date >= start_date)\
     .group_by('month')\
     .order_by('month').all()
    
    # Initialize result lists
    labels = []
    total_invoices = []
    paid_invoices = []
    paystub_amounts = []
    earnings = []
    
    # Fill in the data for all months
    current = start_date
    while current <= today:
        month_str = current.strftime('%b %Y')
        labels.append(month_str)
        
        # Find invoice data for this month
        month_data = next((d for d in monthly_data if d.month.year == current.year and d.month.month == current.month), None)
        total_invoices.append(float(month_data.total_invoiced if month_data else 0))
        paid_amount = float(month_data.total_received if month_data else 0)
        paid_invoices.append(paid_amount)
        
        # Find paystub data for this month
        paystub_data = next((d for d in monthly_paystubs if d.month.year == current.year and d.month.month == current.month), None)
        paystub_amount = float(paystub_data.total_amount if paystub_data else 0)
        paystub_amounts.append(paystub_amount)
        
        # Calculate earnings (paid invoices - paystub amounts)
        earnings.append(paid_amount - paystub_amount)
        
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    return {
        'labels': labels,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'paystub_amounts': paystub_amounts,
        'earnings': earnings
    }


@app.route('/')
def home():
    if current_user.is_authenticated:
        total_employees = Employee.query.count()
        total_clients = Client.query.count()
        total_interventions = Intervention.query.count()
        user_interventions = Intervention.query.join(Employee).filter(Employee.email == current_user.email).count()
        
        # Get employee record for role-based stats
        employee = Employee.query.filter_by(email=current_user.email).first()
        
        # Initialize stats
        org_stats = None
        user_stats = None
        
        # Determine which stats to show based on user type and position
        show_org_stats = False
        show_user_stats = False
        
        if current_user.user_type in ['admin', 'super'] and employee.position == 'Administrator':
            # Admin/super with Administrator position - show only org stats
            show_org_stats = True
        elif current_user.user_type == 'admin' and employee.position in ['Therapist', 'Senior Therapist', 'Behaviour Analyst']:
            # Admin with other positions - show both org and personal stats
            show_org_stats = True
            show_user_stats = True
        else:
            # Regular users (therapists, supervisors) - show only personal stats
            show_user_stats = True
        
        # Get relevant statistics
        if show_org_stats:
            org_stats = get_session_stats()
        if show_user_stats:
            user_stats = get_session_stats(current_user.email)
        
        # Get monthly statistics for the graph
        monthly_data = get_monthly_totals()
        
        return render_template('home.html', 
                            total_employees=total_employees,
                            total_clients=total_clients,
                            user_interventions=user_interventions,
                            total_interventions=total_interventions,
                            org_stats=org_stats,
                            user_stats=user_stats,
                            show_org_stats=show_org_stats,
                            show_user_stats=show_user_stats,
                            org_name=org_name,
                            monthly_labels=monthly_data['labels'],
                            monthly_paid_invoices=monthly_data['paid_invoices'],
                            monthly_total_invoices=monthly_data['total_invoices'],
                            monthly_paystubs=monthly_data['paystub_amounts'],
                            monthly_earnings=monthly_data['earnings'])
    return render_template('home.html', org_name=org_name)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        employee = Employee.query.filter_by(email=form.email.data.lower()).first()
        if not employee:
            flash('Your account is not registered. Contact Administrator.', 'danger')
            return render_template('login.html', form=form, org_name=org_name)
        
        if not employee.login_enabled:
            flash('Your account has not been activated. Contact Administrator.', 'danger')
            return render_template('login.html', form=form, org_name=org_name)
        
        if employee.user_type == "super":
            if employee.check_password(form.password.data):
                login_user(employee)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                if next_page == None or not next_page.startswith('/'):
                    next_page = url_for('home')
                return redirect(next_page)
            else:
                flash('Incorrect password! Try again.', 'danger')
                return render_template('login.html', form=form, org_name=org_name)
        else:
            if not employee.password_hash:
                flash('Your account password has not been set. Contact Administrator.', 'danger')
                return render_template('login.html', form=form, org_name=org_name)

            if employee.failed_attempt == -2:
                flash("Your account has been locked out. Contact Administrator to unlock your account.", "danger")
                return render_template('login.html', form=form, org_name=org_name)
            
            if employee.check_password(form.password.data):
                if employee.locked_until and datetime.now() < employee.locked_until:
                    remaining_time = employee.locked_until - datetime.now()
                    rem_min = int(remaining_time.total_seconds() / 60)
                    rem_sec = int(remaining_time.total_seconds() % 60)
                    flash(f"Wait for {rem_min} min and {rem_sec} sec for your account to unlock automatically or contact Administrator to unlock it immediately.", 'danger')
                    return render_template('login.html', form=form, org_name=org_name)

                employee.failed_attempt = 3
                employee.locked_until = None
                db.session.commit()
                login_user(employee)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                if next_page == None or not next_page.startswith('/'):
                    next_page = url_for('home')
                return redirect(next_page)
            else:
                employee.failed_attempt = employee.failed_attempt-1
                if employee.failed_attempt <= 0:
                    if not employee.locked_until:
                        employee.locked_until = datetime.now()
                    time_to_remain_locked = -(employee.failed_attempt - 1)*15
                    employee.locked_until += timedelta(minutes=time_to_remain_locked)
                    remaining_time = employee.locked_until - datetime.now()
                    rem_min = int(remaining_time.total_seconds() / 60)
                    rem_sec = int(remaining_time.total_seconds() % 60)
                    flash(f"Wait for {rem_min} min and {rem_sec} sec for your account to unlock automatically or contact Administrator to unlock it immediately.", 'danger')
                else:
                    flash(f"Incorrect password! {employee.failed_attempt} remaining attempt(s).", 'danger')
                db.session.commit()
                return render_template('login.html', form=form, org_name=org_name)

    return render_template('login.html', form=form, org_name=org_name)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()

    if request.method == 'POST':
        employee = Employee.query.filter_by(email=form.email.data).first()
        if employee:
            if not employee.password_hash:
                # Check activation key
                if not employee.activation_key or employee.activation_key != form.activation_key.data:
                    flash('Invalid activation key. Please check the key provided by your administrator.', 'danger')
                    return render_template('register.html', form=form, org_name=org_name)
                
                # First time setting up password
                employee.email = form.email.data
                employee.set_password(form.password.data)
                employee.locked_until = None
                employee.failed_attempt = 3
                employee.login_enabled = True  # Enable login access
                # Clear the activation key after successful registration
                employee.activation_key = None
                db.session.commit()
                flash('Account registration complete.', 'success')
                return redirect(url_for('login'))
            else:
                flash('This account is already registered. Use the login page instead.', 'danger')
                return render_template('register.html', form=form, org_name=org_name)
        else:
            flash('This email is not recognized. You must be an employee to register.', 'danger')
            return render_template('register.html', form=form, org_name=org_name)
    return render_template('register.html', form=form, org_name=org_name)


if __name__ == '__main__':
    # Development only
    # app.run(debug=True, host='0.0.0.0', port=int("8080"))
    
    # Production: Use a production WSGI server
    http_server = WSGIServer(('', 8080), app)
    http_server.serve_forever()