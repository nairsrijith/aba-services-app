from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, length
from app.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('No account found with that email. Please register first.')
        

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    activation_key = StringField('Activation key', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), length(min=6, message='Password must be at least 6 characters long')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            if user.activation_key == "":
                raise ValidationError('Email already registered. Please use a different email or contact Administrator.')
        
        

