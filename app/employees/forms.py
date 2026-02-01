from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DecimalField
from wtforms.validators import DataRequired, Email, length, ValidationError
from app.models import Employee
from app.utils.validators import validate_phone_number


def validate_rba_number(form, field):
    if not field.data:  # If empty
        if form.position.data == 'Behaviour Analyst':
            raise ValidationError('RBA Number is required for Behaviour Analysts')
        return
    
    # Check if RBA number is unique
    existing = Employee.query.filter_by(rba_number=field.data).first()
    if existing and (not hasattr(form, 'employee_id') or str(existing.id) != form.employee_id.data):
        raise ValidationError('This RBA Number is already in use')


class AddEmployeeForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    position = SelectField('Designation', validators=[DataRequired()])
    rba_number = StringField('RBA Number', validators=[validate_rba_number])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    cell = StringField('Phone Number', validators=[DataRequired(), validate_phone_number])
    address1 = StringField('Address 1')
    address2 = StringField('Address 2')
    city = StringField('City')
    state = SelectField('State', default='ON')
    zipcode = StringField('Zipcode', validators=[length(max=6)])
    basepay = DecimalField('Base Pay', validators=[DataRequired()], places=2)
    submit = SubmitField('Add')


class UpdateEmployeeForm(FlaskForm):
    employee_id = StringField('Select Employee', validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    position = SelectField('Designation', validators=[DataRequired()])
    rba_number = StringField('RBA Number')
    email = StringField('Email', validators=[DataRequired(), Email()])
    cell = StringField('Phone', validators=[DataRequired(), validate_phone_number])
    address1 = StringField('Address 1')
    address2 = StringField('Address 2')
    city = StringField('City')
    state = SelectField('State')
    zipcode = StringField('Zipcode', validators=[length(max=6)])
    submit = SubmitField('Update')
