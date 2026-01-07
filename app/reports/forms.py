from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, BooleanField, SelectField
from wtforms.widgets import CheckboxInput, ListWidget
from app.models import Employee, Designation, Client

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class ClientReportForm(FlaskForm):
    columns = MultiCheckboxField('Columns', choices=[
        ('name', 'Name'),
        ('dob', 'Date of Birth'),
        ('gender', 'Gender'),
        ('parent', 'Parent'),
        ('parent_email', 'Parent Email'),
        ('parent_cell', 'Parent Cell'),
        ('supervisor', 'Supervisor'),
        ('active', 'Active'),
        ('city', 'City'),
        ('state', 'State'),
        ('zipcode', 'Zipcode')
    ], default=['name', 'dob', 'gender', 'parent', 'parent_email', 'parent_cell', 'supervisor', 'active'])
    
    city_filter = SelectMultipleField('Cities', coerce=str)
    state_filter = SelectMultipleField('States', coerce=str)
    supervisor_filter = SelectMultipleField('Supervisors', coerce=int)
    submit = SubmitField('Generate Report')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor_filter.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).all()]
        cities = Client.query.with_entities(Client.city).distinct().filter(Client.city.isnot(None)).filter(Client.city != '').all()
        self.city_filter.choices = [(c[0], c[0]) for c in cities]
        states = Client.query.with_entities(Client.state).distinct().filter(Client.state.isnot(None)).filter(Client.state != '').all()
        self.state_filter.choices = [(s[0], s[0]) for s in states]

class EmployeeReportForm(FlaskForm):
    columns = MultiCheckboxField('Columns', choices=[
        ('name', 'Name'),
        ('position', 'Position'),
        ('email', 'Email'),
        ('cell', 'Cell'),
        ('address', 'Address'),
        ('active', 'Active')
    ], default=['name', 'position', 'email', 'cell', 'active'])
    
    city_filter = SelectMultipleField('Cities', coerce=str)
    state_filter = SelectMultipleField('States', coerce=str)
    active_filter = SelectField('Status', choices=[('all', 'All'), ('active', 'Active'), ('inactive', 'Inactive')], default='all')
    position_filter = SelectMultipleField('Positions', coerce=str)
    submit = SubmitField('Generate Report')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position_filter.choices = [(d.designation, d.designation) for d in Designation.query.all()]
        cities = Employee.query.with_entities(Employee.city).distinct().filter(Employee.city.isnot(None)).filter(Employee.city != '').all()
        self.city_filter.choices = [(c[0], c[0]) for c in cities]
        states = Employee.query.with_entities(Employee.state).distinct().filter(Employee.state.isnot(None)).filter(Employee.state != '').all()
        self.state_filter.choices = [(s[0], s[0]) for s in states]