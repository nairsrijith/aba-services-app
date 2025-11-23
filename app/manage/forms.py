from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, SelectField
from wtforms.validators import DataRequired, length
from app.models import Employee
from flask_wtf.file import FileField, FileAllowed
from wtforms import BooleanField, IntegerField, PasswordField

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'svg'}


class DesignationForm(FlaskForm):
    name = StringField('Designation Name', validators=[DataRequired(), length(max=51)])
    submit = SubmitField('Add Designation')


class ActivityForm(FlaskForm):
    name = StringField('Activity Name', validators=[DataRequired(), length(max=51)])
    category = SelectField('Category', validators=[DataRequired(), length(max=51)])
    submit = SubmitField('Add Activity')


class SettingsForm(FlaskForm):
    org_name = StringField('Organization Name', validators=[length(max=200)])
    org_address = StringField('Organization Address', validators=[length(max=500)])
    org_phone = StringField('Organization Phone', validators=[length(max=50)])
    org_email = StringField('Organization Email', validators=[length(max=120)])
    payment_email = StringField('Payment Email', validators=[length(max=120)])
    logo_file = FileField('Organization Logo', validators=[FileAllowed(list(ALLOWED_IMAGE_EXT), 'Images only')])

    smtp_host = StringField('SMTP Host', validators=[length(max=200)])
    smtp_port = IntegerField('SMTP Port')
    smtp_user = StringField('SMTP User', validators=[length(max=200)])
    smtp_pass = PasswordField('SMTP Password')
    smtp_use_tls = BooleanField('Use TLS')
    smtp_use_ssl = BooleanField('Use SSL')

    testing_mode = BooleanField('Enable Email Testing Mode')
    testing_email = StringField('Testing Email Address', validators=[length(max=120)])

    submit = SubmitField('Save Settings')