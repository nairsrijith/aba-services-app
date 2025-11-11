from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, TimeField, SelectField, FileField
from wtforms.validators import DataRequired
from app.models import Intervention, Employee
from flask import flash


class AddInterventionForm(FlaskForm):
    def validate_session_time(self):
        """Validate that there are no overlapping sessions for the employee"""
        
        if not all([self.employee_id.data, self.date.data, self.start_time.data, self.end_time.data]):
            flash('Please fill in all session time fields.', 'danger')
            return False

        if self.start_time.data >= self.end_time.data:
            flash('End time must be after start time.', 'danger')
            return False

        if Intervention.has_overlap(
            employee_id=int(self.employee_id.data),
            date=self.date.data,
            start_time=self.start_time.data,
            end_time=self.end_time.data
        ):
            employee = Employee.query.get(int(self.employee_id.data))
            flash(f'Schedule conflict: {employee.firstname} {employee.lastname} already has a session scheduled during {self.date.data.strftime("%Y-%m-%d")} {self.start_time.data.strftime("%H:%M")} - {self.end_time.data.strftime("%H:%M")}.', 'danger')
            return False
            
        return True

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
    def __init__(self, *args, **kwargs):
        self.intervention_id = kwargs.pop('intervention_id', None)
        super(UpdateInterventionForm, self).__init__(*args, **kwargs)

    def validate_session_time(self):
        """Validate that there are no overlapping sessions for the employee"""
        
        if not all([self.employee_id.data, self.date.data, self.start_time.data, self.end_time.data]):
            flash('Please fill in all session time fields.', 'danger')
            return False

        if self.start_time.data >= self.end_time.data:
            flash('End time must be after start time.', 'danger')
            return False

        if Intervention.has_overlap(
            employee_id=int(self.employee_id.data),
            date=self.date.data,
            start_time=self.start_time.data,
            end_time=self.end_time.data,
            exclude_id=self.intervention_id
        ):
            employee = Employee.query.get(int(self.employee_id.data))
            flash(f'Schedule conflict: {employee.firstname} {employee.lastname} already has a session scheduled during {self.date.data.strftime("%Y-%m-%d")} {self.start_time.data.strftime("%H:%M")} - {self.end_time.data.strftime("%H:%M")}.', 'danger')
            return False
            
        return True

    client_id = SelectField('Select Client', validators=[DataRequired()]) # client_id is a foreign key to the Client model
    employee_id = SelectField('Select Employee', validators=[DataRequired()]) # employee_id is a foreign key to the Employee model
    intervention_type = SelectField('Intervention Type', validators=[DataRequired()])
    date = DateField('Intervention Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired()])  # in hours e.g., '1.5' for 1 hour 30 minutes
    # Make invoiced optional for update form; it will be set when the form is submitted if present
    invoiced = StringField('Invoiced')  # e.g., 'Yes' or 'No'
    invoice_number = StringField('Invoice Number')  # optional field for invoice number if invoiced
    file_names = FileField('File(s) to add')  # optional field for filename if a file is uploaded
    submit = SubmitField('Update')

