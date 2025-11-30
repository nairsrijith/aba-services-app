from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_wtf.file import FileField, FileAllowed


class SetRoleForm(FlaskForm):
    user_type = SelectField('Role', validators=[DataRequired()], 
                          choices=[("admin", "Admin"), ("supervisor", "Supervisor"), 
                                 ("therapist", "Therapist")],
                          default="therapist")
    submit = SubmitField('Update Role')


class UpdatePasswordForm(FlaskForm):
    # Make password fields optional at form-level; validate in the view only when
    # the user chooses to update the password. This allows the same form to be
    # used to update only the profile picture.
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm New Password')
    profile_pic = FileField('Profile Picture', validators=[FileAllowed(['jpg','jpeg','png','gif'], 'Images only')])
    submit = SubmitField('Update')