from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DecimalField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional


class PayRateForm(FlaskForm):
    employee = SelectField('Employee', validators=[DataRequired()])
    client = SelectField('Client', validators=[Optional()])  # Optional for base rate
    rate = DecimalField('Hourly Rate', validators=[DataRequired()], places=2)
    effective_date = DateField('Effective Date', validators=[Optional()])
    submit = SubmitField('Save')


class PayPeriodForm(FlaskForm):
    employee = SelectField('Employee', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Preview')
    save = SubmitField('Save Paystub')
