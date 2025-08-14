from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, SelectMultipleField, SubmitField, StringField
from wtforms.validators import DataRequired


class InvoiceClientSelectionForm(FlaskForm):
    client_id = SelectField('Client', validators=[DataRequired()])
    date_from = DateField('From', format='%Y-%m-%d', validators=[DataRequired()])
    date_to = DateField('To', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Select Interventions')


class InvoicePreviewForm(FlaskForm):
    client_name = StringField('Client Name', validators=[DataRequired()])
    parent_name = StringField('Parent/Guardian Name')
    address = StringField('Address')
    invoice_number = StringField('Invoice Number', validators=[DataRequired()])
    invoice_date = DateField('Invoice Date', format='%Y-%m-%d', validators=[DataRequired()])
    payby_date = DateField('Pay By Date', format='%Y-%m-%d', validators=[DataRequired()])
    interventions = SelectMultipleField('Interventions', choices=[])
    date_from = DateField('From', validators=[DataRequired()])
    date_to = DateField('To', validators=[DataRequired()])
    submit = SubmitField('Confirm and Save Invoice')