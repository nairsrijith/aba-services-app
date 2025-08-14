from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, FloatField
from wtforms.validators import DataRequired, Email


class AddClientForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()], default='Unspecified')
    parentname = StringField('Parent Name', validators=[DataRequired()])
    parentemail = StringField('Parent Email', validators=[DataRequired(), Email()])
    parentcell = StringField('Parent Phone', validators=[DataRequired()])
    address1 = StringField('Address', validators=[DataRequired()])
    address2 = StringField('Address 2')
    city = StringField('City', validators=[DataRequired()])
    state = SelectField('State', validators=[DataRequired()], default='ON')
    zipcode = StringField('Zipcode', validators=[DataRequired()])
    cost_supervision = FloatField('Supervision Cost', default=0.0)
    cost_therapy = FloatField('Therapy Cost', default=0.0)
    submit = SubmitField('Add')


class UpdateClientForm(FlaskForm):
    client_id = SelectField('Select Client', coerce=int, validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()])
    parentname = StringField('Parent Name', validators=[DataRequired()])
    parentemail = StringField('Parent Email', validators=[DataRequired(), Email()])
    parentcell = StringField('Parent Phone', validators=[DataRequired()])
    address1 = StringField('Address', validators=[DataRequired()])
    address2 = StringField('Address 2')
    city = StringField('City', validators=[DataRequired()])
    state = SelectField('State', validators=[DataRequired()])
    zipcode = StringField('Zipcode', validators=[DataRequired()])
    cost_supervision = FloatField('Supervision Cost', default=0.0)
    cost_therapy = FloatField('Therapy Cost', default=0.0)
    submit = SubmitField('Update', validators=[DataRequired()])
