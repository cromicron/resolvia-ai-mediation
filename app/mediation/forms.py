from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class MediationForm(FlaskForm):
    """Form to start new mediation"""
    title = StringField('Title', validators=[DataRequired()])
    invitee = StringField('Username or Email', validators=[DataRequired()])
    submit = SubmitField('Start Mediation')
