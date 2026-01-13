from flask import Blueprint, render_template, request, abort
from app import db
from app.models import Employee, Client, Intervention, Invoice, PayStub
from flask_login import login_required, current_user
from app.utils.settings_utils import get_org_settings
from datetime import date, timedelta
from app.reports.forms import ClientReportForm, EmployeeReportForm

reports_bp = Blueprint('reports', __name__, template_folder='templates')

@reports_bp.route('/employees', methods=['GET', 'POST'])
@login_required
def employees_report():
    if not (current_user.is_authenticated and current_user.position == 'Administrator'):
        abort(403)
    
    form = EmployeeReportForm()
    selected_columns = ['name', 'position', 'email', 'cell', 'active']
    employees = Employee.query.filter(Employee.user_type != 'super')
    
    if request.method == 'POST' and form.validate_on_submit():
        selected_columns = form.columns.data
        if 'position' in selected_columns and form.position_filter.data:
            employees = employees.filter(Employee.position.in_(form.position_filter.data))
        if 'address' in selected_columns:
            if form.city_filter.data:
                employees = employees.filter(Employee.city.in_(form.city_filter.data))
            if form.state_filter.data:
                employees = employees.filter(Employee.state.in_(form.state_filter.data))
        if 'active' in selected_columns and form.active_filter.data != 'all':
            is_active = form.active_filter.data == 'active'
            employees = employees.filter(Employee.is_active == is_active)
    
    employees = employees.all()
    settings = get_org_settings()
    return render_template('employees_report.html', employees=employees, selected_columns=selected_columns, form=form, org_name=settings['org_name'])

@reports_bp.route('/clients', methods=['GET', 'POST'])
@login_required
def clients_report():
    if not (current_user.is_authenticated and current_user.position == 'Administrator'):
        abort(403)
    
    form = ClientReportForm()
    selected_columns = ['name', 'dob', 'gender', 'parent', 'parent_email', 'parent_cell', 'supervisor', 'active']
    clients = Client.query.filter_by(is_active=True)
    
    if request.method == 'POST' and form.validate_on_submit():
        selected_columns = form.columns.data
        if 'city' in selected_columns and form.city_filter.data:
            clients = clients.filter(Client.city.in_(form.city_filter.data))
        if 'state' in selected_columns and form.state_filter.data:
            clients = clients.filter(Client.state.in_(form.state_filter.data))
        if 'supervisor' in selected_columns and form.supervisor_filter.data:
            clients = clients.filter(Client.supervisor_id.in_(form.supervisor_filter.data))
    
    clients = clients.all()
    settings = get_org_settings()
    return render_template('clients_report.html', clients=clients, selected_columns=selected_columns, form=form, org_name=settings['org_name'])

@reports_bp.route('/sessions')
@login_required
def sessions_report():
    if not (current_user.is_authenticated and current_user.position == 'Administrator'):
        abort(403)
    
    # Default to current month
    start_date_str = request.args.get('start_date')
    if start_date_str:
        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = date.today().replace(day=1)
    
    end_date_str = request.args.get('end_date')
    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        end_date = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    interventions = Intervention.query.filter(
        Intervention.date >= start_date,
        Intervention.date <= end_date
    )
    
    client_id = request.args.get('client_id')
    if client_id:
        interventions = interventions.filter(Intervention.client_id == int(client_id))
    
    employee_id = request.args.get('employee_id')
    if employee_id:
        interventions = interventions.filter(Intervention.employee_id == int(employee_id))
    
    interventions = interventions.order_by(Intervention.date).all()
    
    clients = Client.query.filter_by(is_active=True).order_by(Client.firstname).all()
    employees = Employee.query.filter(Employee.position != 'Administrator').order_by(Employee.firstname).all()
    
    settings = get_org_settings()
    return render_template('sessions_report.html', interventions=interventions, start_date=start_date.isoformat(), end_date=end_date.isoformat(), clients=clients, employees=employees, org_name=settings['org_name'])

@reports_bp.route('/invoices')
@login_required
def invoices_report():
    if not (current_user.is_authenticated and current_user.position == 'Administrator'):
        abort(403)
    
    # Default to current month
    start_date_str = request.args.get('start_date')
    if start_date_str:
        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = date.today().replace(day=1)
    
    end_date_str = request.args.get('end_date')
    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        end_date = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    invoices = Invoice.query.filter(
        Invoice.invoiced_date >= start_date,
        Invoice.invoiced_date <= end_date
    )
    
    client_id = request.args.get('client_id')
    if client_id:
        invoices = invoices.filter(Invoice.client_id == int(client_id))
    
    invoices = invoices.order_by(Invoice.invoiced_date.desc()).all()
    
    clients = Client.query.filter_by(is_active=True).order_by(Client.firstname).all()
    
    settings = get_org_settings()
    return render_template('invoices_report.html', invoices=invoices, start_date=start_date.isoformat(), end_date=end_date.isoformat(), clients=clients, org_name=settings['org_name'])

@reports_bp.route('/paystubs')
@login_required
def paystubs_report():
    if not (current_user.is_authenticated and current_user.position == 'Administrator'):
        abort(403)
    
    # Default to current month
    start_date_str = request.args.get('start_date')
    if start_date_str:
        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = date.today().replace(day=1)
    
    end_date_str = request.args.get('end_date')
    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        end_date = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    paystubs = PayStub.query.filter(
        PayStub.generated_date >= start_date,
        PayStub.generated_date <= end_date
    )
    
    employee_id = request.args.get('employee_id')
    if employee_id:
        paystubs = paystubs.filter(PayStub.employee_id == int(employee_id))
    
    paystubs = paystubs.order_by(PayStub.generated_date.desc()).all()
    
    employees = Employee.query.filter(Employee.position != 'Administrator').order_by(Employee.firstname).all()
    
    settings = get_org_settings()
    return render_template('paystubs_report.html', paystubs=paystubs, start_date=start_date.isoformat(), end_date=end_date.isoformat(), employees=employees, org_name=settings['org_name'])