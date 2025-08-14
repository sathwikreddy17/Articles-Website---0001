from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class ArticleForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    tags = StringField("Tags (comma-separated)")
    body = TextAreaField("Body", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
