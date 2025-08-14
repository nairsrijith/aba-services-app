from flask import Blueprint, render_template, redirect, url_for, request
from app import db
from app.models import Employee, Designation
from app.employees.forms import AddEmployeeForm, UpdateEmployeeForm

employees_bp = Blueprint('employees', __name__, template_folder='templates')


@employees_bp.route('/add', methods=['GET', 'POST'])
def add_employee():
    form = AddEmployeeForm()
    form.position.choices = [(d.designation, d.designation) for d in Designation.query.all()]
    form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                          ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                          ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                          ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                          ("NU", "Nunavut"), ("YT", "Yukon")]

    if form.validate_on_submit():
        new_employee = Employee(firstname=form.firstname.data.title(),
                                lastname=form.lastname.data.title(),
                                position=form.position.data.title(),
                                email=form.email.data,
                                cell=form.cell.data,
                                address1=form.address1.data.title(),
                                address2=form.address2.data.title(),
                                city=form.city.data.title(),
                                state=form.state.data,
                                zipcode=form.zipcode.data.upper())
        db.session.add(new_employee)
        db.session.commit()
        return redirect(url_for('employees.list_employees'))
    return render_template('add_emp.html', form=form)


@employees_bp.route('/list', methods=['GET', 'POST'])
def list_employees():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    employees_pagination = Employee.query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        'list_emp.html',
        employees=employees_pagination.items,
        pagination=employees_pagination,
        per_page=per_page
    )


@employees_bp.route('/delete/<int:employee_id>', methods=['GET', 'POST'])
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    return redirect(url_for('employees.list_employees'))


@employees_bp.route('/update/<int:employee_id>', methods=['GET', 'POST'])
def update_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = UpdateEmployeeForm(obj=employee)
    
    form.populate_obj(employee)
    form.position.choices = [(d.designation, d.designation) for d in Designation.query.all()]
    form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                          ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                          ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                          ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                          ("NU", "Nunavut"), ("YT", "Yukon")]

    if request.method == 'POST':
        employee.firstname = form.firstname.data.title()
        employee.lastname = form.lastname.data.title()
        employee.position = form.position.data.title()
        employee.email = form.email.data
        employee.cell = form.cell.data
        employee.address1 = form.address1.data.title()
        employee.address2 = form.address2.data.title()
        employee.city = form.city.data.title()
        employee.state = form.state.data
        employee.zipcode = form.zipcode.data.upper()
        db.session.commit()
        return redirect(url_for('employees.list_employees'))
    return render_template('update_emp.html', form=form, employee=employee)


