from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email


class AddEmployeeForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    position = SelectField('Designation', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    cell = StringField('Phone Number', validators=[DataRequired()])
    address1 = StringField('Address 1')
    address2 = StringField('Address 2')
    city = StringField('City')
    state = SelectField('State', default='ON')
    zipcode = StringField('Zipcode')
    submit = SubmitField('Add')


class UpdateEmployeeForm(FlaskForm):
    employee_id = StringField('Select Employee', validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    position = SelectField('Designation', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    cell = StringField('Phone', validators=[DataRequired()])
    address1 = StringField('Address 1')
    address2 = StringField('Address 2')
    city = StringField('City')
    state = SelectField('State')
    zipcode = StringField('Zipcode')
    submit = SubmitField('Update')
