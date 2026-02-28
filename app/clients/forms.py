from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, FloatField
from wtforms.validators import DataRequired, Email, length, Optional
from app.utils.validators import validate_phone_number


class AddClientForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()], default='Unspecified')
    
    # Parent 1 fields
    parent_firstname = StringField('Parent First Name', validators=[DataRequired()])
    parent_lastname = StringField('Parent Last Name')
    parent_email = StringField('Parent Email', validators=[DataRequired(), Email()])
    parent_cell = StringField('Parent Phone', validators=[DataRequired()])
    
    # Parent 2 fields (optional)
    parent2_firstname = StringField('Second Parent First Name', validators=[Optional()])
    parent2_lastname = StringField('Second Parent Last Name', validators=[Optional()])
    parent2_email = StringField('Second Parent Email', validators=[Optional(), Email()])
    parent2_cell = StringField('Second Parent Phone', validators=[Optional()])
    
    address1 = StringField('Address', validators=[DataRequired()])
    address2 = StringField('Address 2')
    city = StringField('City', validators=[DataRequired()])
    state = SelectField('State', validators=[DataRequired()], default='ON')
    zipcode = StringField('Zipcode', validators=[DataRequired(), length(max=6)])
    supervisor_id = SelectField('Supervisor', coerce=int, validators=[DataRequired()])
    cost_supervision = FloatField('Supervision Cost', default=0.0)
    cost_therapy = FloatField('Therapy Cost', default=0.0)
    submit = SubmitField('Add')


class UpdateClientForm(FlaskForm):
    client_id = SelectField('Select Client', coerce=int, validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name')
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()])
    
    # Parent 1 fields
    parent_firstname = StringField('Parent First Name', validators=[DataRequired()])
    parent_lastname = StringField('Parent Last Name')
    parent_email = StringField('Parent Email', validators=[DataRequired(), Email()])
    parent_cell = StringField('Parent Phone', validators=[DataRequired()])
    
    # Parent 2 fields (optional)
    parent2_firstname = StringField('Second Parent First Name', validators=[Optional()])
    parent2_lastname = StringField('Second Parent Last Name', validators=[Optional()])
    parent2_email = StringField('Second Parent Email', validators=[Optional(), Email()])
    parent2_cell = StringField('Second Parent Phone', validators=[Optional()])
    
    address1 = StringField('Address', validators=[DataRequired()])
    address2 = StringField('Address 2')
    city = StringField('City', validators=[DataRequired()])
    state = SelectField('State', validators=[DataRequired()])
    zipcode = StringField('Zipcode', validators=[DataRequired(), length(max=6)])
    supervisor_id = SelectField('Supervisor', coerce=int, validators=[DataRequired()])
    cost_supervision = FloatField('Supervision Cost', default=0.0)
    cost_therapy = FloatField('Therapy Cost', default=0.0)
    submit = SubmitField('Update', validators=[DataRequired()])
