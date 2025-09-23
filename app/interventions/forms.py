from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, TimeField, SelectField, FileField
from wtforms.validators import DataRequired


class AddInterventionForm(FlaskForm):
    client_id = SelectField('Select Client', validators=[DataRequired()]) # client_id is a foreign key to the Client model
    employee_id = SelectField('Select Employee', validators=[DataRequired()]) # employee_id is a foreign key to the Employee model
    intervention_type = SelectField('Intervention Type', default="Therapy", validators=[DataRequired()])
    date = DateField('Intervention Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired()])  # in hours e.g., '1.5' for 1 hour 30 minutes
    invoiced = StringField('Invoiced')  # e.g., 'Yes' or 'No'
    file_names = FileField('File(s) to add')  # optional field for filename if a file is uploaded
    invoice_number = StringField('Invoice Number')  # optional field for invoice number if invoiced
    submit = SubmitField('Add')


class UpdateInterventionForm(FlaskForm):
    client_id = SelectField('Select Client', validators=[DataRequired()]) # client_id is a foreign key to the Client model
    employee_id = SelectField('Select Employee', validators=[DataRequired()]) # employee_id is a foreign key to the Employee model
    intervention_type = SelectField('Intervention Type', validators=[DataRequired()])
    date = DateField('Intervention Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired()])  # in hours e.g., '1.5' for 1 hour 30 minutes
    invoiced = StringField('Invoiced', validators=[DataRequired()])  # e.g., 'Yes' or 'No'
    invoice_number = StringField('Invoice Number')  # optional field for invoice number if invoiced
    file_names = FileField('File(s) to add')  # optional field for filename if a file is uploaded
    submit = SubmitField('Update')

