from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, SelectField, DateField, TextAreaField, FloatField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, NumberRange
from datetime import date

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class HomeForm(FlaskForm):
    name = StringField('Home Name', validators=[DataRequired(), Length(min=1, max=100)])
    submit = SubmitField('Create Home')

class ChoreForm(FlaskForm):
    name = StringField('Chore Name', validators=[DataRequired(), Length(min=1, max=100)])
    submit = SubmitField('Add Chore')

class ChoreCompletionForm(FlaskForm):
    chore_id = HiddenField('Chore ID', validators=[DataRequired()])
    user_id = HiddenField('User ID', validators=[DataRequired()])
    completion_date = DateField('Completion Date', validators=[DataRequired()], default=date.today)
    is_shared = BooleanField('Share with another user?')
    percentage = IntegerField('Your Percentage (%)', validators=[Optional(), NumberRange(min=1, max=99)])
    other_user_id = SelectField('Other User', coerce=int, validators=[Optional()])
    submit = SubmitField('Complete Chore')

class ChoreAssignmentForm(FlaskForm):
    chore_id = SelectField('Chore', coerce=int, validators=[DataRequired()])
    assignee_id = SelectField('Assign To', coerce=int, validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()], default=date.today)
    points = FloatField('Points', validators=[DataRequired()], default=1.0)
    notes = TextAreaField('Notes', validators=[Optional()])
    add_to_calendar = BooleanField('Add to Google Calendar', default=True)
    submit = SubmitField('Assign Chore')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    home_id = SelectField('Home', coerce=int, validators=[DataRequired()])
    is_admin = BooleanField('Admin Access')
    submit = SubmitField('Update User') 