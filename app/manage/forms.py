from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired, length
from app.models import User


class DesignationForm(FlaskForm):
    name = StringField('Designation Name', validators=[DataRequired(), length(max=51)])
    submit = SubmitField('Add Designation')


class ActivityForm(FlaskForm):
    name = StringField('Activity Name', validators=[DataRequired(), length(max=51)])
    category = StringField('Category', validators=[DataRequired(), length(max=51)])
    submit = SubmitField('Add Activity')