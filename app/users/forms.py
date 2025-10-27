from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo


class AddUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    # 'therapist' replaces the previous 'user' role. 'supervisor' can be created by admins if needed.
    user_type = SelectField('User type', validators=[DataRequired()], default="therapist")
    submit = SubmitField('Add')


class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')