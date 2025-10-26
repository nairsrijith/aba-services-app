from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app import db
from app.models import Employee, Designation, Intervention, Client
from app.employees.forms import AddEmployeeForm, UpdateEmployeeForm
from flask_login import login_required, current_user
import os
import re

employees_bp = Blueprint('employees', __name__, template_folder='templates')

org_name = os.environ.get('ORG_NAME', 'My Organization')

@employees_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.is_authenticated and current_user.user_type == "admin":
        form = AddEmployeeForm()
        form.position.choices = [(d.designation, d.designation) for d in Designation.query.all()]
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]

        if form.validate_on_submit():
            try:
                # Set rba_number to None if position is not Behaviour Analyst
                rba_number = form.rba_number.data if form.position.data == 'Behaviour Analyst' else None
                
                # Validate RBA number requirement for Behaviour Analyst
                if form.position.data == 'Behaviour Analyst' and not rba_number:
                    form.rba_number.errors.append('RBA Number is required for Behaviour Analysts')
                    return render_template('add_emp.html', form=form, org_name=org_name)
                
                # Normalize phone number to digits-only before storing (DB column is String(10))
                normalized_cell = re.sub(r'\D', '', (form.cell.data or ''))

                new_employee = Employee(firstname=form.firstname.data.title(),
                                    lastname=form.lastname.data.title(),
                                    position=form.position.data.title(),
                                    rba_number=rba_number,
                                    email=form.email.data,
                                    cell=normalized_cell,
                                    address1=form.address1.data.title(),
                                    address2=form.address2.data.title(),
                                    city=form.city.data.title(),
                                    state=form.state.data,
                                    zipcode=form.zipcode.data.upper())
                db.session.add(new_employee)
                db.session.flush()  # get new_employee.id before commit

                # Add base pay rate for new employee (client_id=None means base rate)
                base_rate = 25.0  # Default base rate, can be changed or set via form later
                from app.models import PayRate
                base_payrate = PayRate(employee_id=new_employee.id, client_id=None, rate=base_rate, effective_date=None)
                db.session.add(base_payrate)
                db.session.commit()
                flash('Employee added successfully! Base pay rate set to ${:.2f}.'.format(base_rate), 'success')
                return redirect(url_for('employees.list_employees'))
            except Exception as e:
                db.session.rollback()
                if 'employees_rba_number_key' in str(e):
                    form.rba_number.errors.append('This RBA Number is already in use')
                    return render_template('add_emp.html', form=form, org_name=org_name)
                flash('Error adding employee. Please check the form and try again.', 'danger')
                return render_template('add_emp.html', form=form, org_name=org_name)
        return render_template('add_emp.html', form=form, org_name=org_name)
    else:
        abort(403)


@employees_bp.route('/deactivate/<int:employee_id>', methods=['POST'])
@login_required
def deactivate_employee(employee_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        employee = Employee.query.get_or_404(employee_id)
        
        # Only allow deactivation if employee is not a supervisor for any active clients
        active_clients = Client.query.filter_by(supervisor_id=employee.id, is_active=True).all()
        if active_clients:
            flash('Cannot deactivate employee who is supervising active clients. Please reassign their clients first.', 'danger')
            return redirect(url_for('employees.list_employees'))

        employee.is_active = False
        db.session.commit()
        flash('Employee has been deactivated.', 'success')
        return redirect(url_for('employees.list_employees'))
    else:
        abort(403)


@employees_bp.route('/reactivate/<int:employee_id>', methods=['POST'])
@login_required
def reactivate_employee(employee_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        employee = Employee.query.get_or_404(employee_id)
        employee.is_active = True
        db.session.commit()
        flash('Employee has been reactivated.', 'success')
        return redirect(url_for('employees.list_employees'))
    else:
        abort(403)


@employees_bp.route('/list', methods=['GET', 'POST'])
@login_required
def list_employees():
    if current_user.is_authenticated and current_user.user_type == "admin":
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        # Respect the `show_inactive` toggle: when not set, only show active employees.
        show_inactive = request.args.get('show_inactive', '0')
        if show_inactive == '1':
            # include both active and inactive, active first
            query = Employee.query.order_by(Employee.is_active.desc(), Employee.firstname, Employee.lastname)
        else:
            # only active employees
            query = Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname)
        employees_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return render_template(
            'list_emp.html',
            employees=employees_pagination.items,
            pagination=employees_pagination,
            per_page=per_page,
            org_name=org_name
        )
    else:
        abort(403)


@employees_bp.route('/delete/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def delete_employee(employee_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        employee = Employee.query.get_or_404(employee_id)
        interventions = Intervention.query.filter_by(employee_id=employee.id).all()
        if interventions:
            flash('Cannot delete employee with associated interventions. Please reassign or delete interventions first.', 'danger')
            return redirect(url_for('employees.list_employees'))
        clients = Client.query.filter_by(supervisor_id=employee.id).all()
        if clients:
            flash('Cannot delete employee who is a supervisor for clients. Please reassign client to another supervisor.', 'danger')
            return redirect(url_for('employees.list_employees'))
        db.session.delete(employee)
        db.session.commit()
        return redirect(url_for('employees.list_employees'))
    else:
        abort(403)


@employees_bp.route('/update/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def update_employee(employee_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        employee = Employee.query.get_or_404(employee_id)
        form = UpdateEmployeeForm(obj=employee)
        form.employee_id.data = str(employee_id)  # Set the employee_id field
        form.position.choices = [(d.designation, d.designation) for d in Designation.query.all()]
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]

        if form.validate_on_submit():
            try:
                # Set rba_number to None if position is not Behaviour Analyst
                rba_number = form.rba_number.data if form.position.data == 'Behaviour Analyst' else None
                
                employee.firstname = form.firstname.data.title()
                employee.lastname = form.lastname.data.title()
                employee.position = form.position.data.title()
                employee.rba_number = rba_number
                employee.email = form.email.data
                # Store digits-only phone number to match DB column
                employee.cell = re.sub(r'\D', '', (form.cell.data or ''))
                employee.address1 = form.address1.data.title()
                employee.address2 = form.address2.data.title()
                employee.city = form.city.data.title()
                employee.state = form.state.data
                employee.zipcode = form.zipcode.data.upper()
                db.session.commit()
                flash('Employee updated successfully!', 'success')
                return redirect(url_for('employees.list_employees'))
            except Exception as e:
                db.session.rollback()
                flash('Error updating employee. Please check the form and try again.', 'danger')
                return render_template('update_emp.html', form=form, employee=employee, org_name=org_name)
        return render_template('update_emp.html', form=form, employee=employee, org_name=org_name)
    else:
        abort(403)


