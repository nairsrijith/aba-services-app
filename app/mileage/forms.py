from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DecimalField, StringField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional, NumberRange


class MileageRateForm(FlaskForm):
    """Form for creating/updating mileage rates"""
    rate = DecimalField('Rate per Mile ($)', validators=[DataRequired(), NumberRange(min=0.01)], places=4)
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    submit = SubmitField('Save Mileage Rate')


class MileageForm(FlaskForm):
    """Form for recording individual mileage entries"""
    employee = SelectField('Employee', validators=[DataRequired()])
    client = SelectField('Client', validators=[DataRequired()])
    date = DateField('Date of Travel', validators=[DataRequired()])
    distance = DecimalField('Distance (Kilometers)', validators=[DataRequired(), NumberRange(min=0.1)], places=2)
    description = StringField('Description (Optional)', validators=[Optional()])
    submit = SubmitField('Save Mileage Entry')
