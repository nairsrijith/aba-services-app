from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, length
from app.models import Employee


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

    def validate_email(self, email):
        employee = Employee.query.filter_by(email=email.data.lower()).first()
        if employee is None:
            raise ValidationError('No account found with that email. Contact administrator to be added as an employee first.')
        

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    activation_key = StringField('Activation Key', validators=[DataRequired(), length(min=8, max=8, message='Activation key must be 8 characters')])
    password = PasswordField('Password', validators=[DataRequired(), length(min=6, message='Password must be at least 6 characters long')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        employee = Employee.query.filter_by(email=email.data.lower()).first()
        if not employee:
            raise ValidationError('You must be added as an employee before you can register.')
        if employee.password_hash:
            raise ValidationError('Account already registered. Please use the login page.')
        
        

