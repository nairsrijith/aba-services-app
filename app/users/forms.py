from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email


class AddUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    user_type = SelectField('User type', validators=[DataRequired()], default="user")
    activation_key = StringField('Activation key', validators=[DataRequired()])
    submit = SubmitField('Add')