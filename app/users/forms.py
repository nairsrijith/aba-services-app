from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo


class SetRoleForm(FlaskForm):
    user_type = SelectField('Role', validators=[DataRequired()], 
                          choices=[("admin", "Admin"), ("supervisor", "Supervisor"), 
                                 ("therapist", "Therapist")],
                          default="therapist")
    submit = SubmitField('Update Role')


class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')