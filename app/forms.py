# app/forms.py
from flask_wtf import FlaskForm
# Añadir BooleanField para is_admin
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField
# Añadir Optional para contraseña opcional
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User
from app import db

# --- Formulario de Login (sin cambios) ---
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

# --- Formulario de Observación (sin cambios) ---
class ObservationForm(FlaskForm):
    classification_choices = [
        ('', '-- Seleccione Clasificación --'),
        ('Correo Recibido', 'Correo Recibido'),
        ('Llamada Recibida', 'Llamada Recibida'),
        ('Visita Anunciada', 'Visita Anunciada'),
        ('Visita No Anunciada', 'Visita No Anunciada'),
        ('Ronda de Seguridad', 'Ronda de Seguridad'),
        ('Incidente Menor', 'Incidente Menor'),
        ('Incidente Mayor', 'Incidente Mayor'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Solicitud Residente', 'Solicitud Residente'),
        ('Otro', 'Otro')
    ]
    classification = SelectField(
        'Clasificación',
        choices=classification_choices,
        validators=[DataRequired(message="Debe seleccionar una clasificación.")]
    )
    body = TextAreaField(
        'Descripción de la Observación',
        validators=[
            DataRequired(message="La descripción no puede estar vacía."),
            Length(min=5, max=500, message="La descripción debe tener entre 5 y 500 caracteres.")
        ],
        render_kw={"rows": 4}
    )
    submit = SubmitField('Registrar Observación')

# --- Formulario de Registro (sin cambios) ---
class RegistrationForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    submit = SubmitField('Registrar Usuario')

    def validate_username(self, username):
        user = db.session.scalar(db.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('Este nombre de usuario ya está en uso. Por favor, elige otro.')

# --- Formulario de Búsqueda (sin cambios) ---
class SearchForm(FlaskForm):
    query = StringField('Buscar en observaciones', validators=[DataRequired()])
    submit = SubmitField('Buscar')

# --- Nuevo Formulario para Editar Usuario ---
class EditUserForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=3, max=64)])
    # Contraseña opcional: solo se valida si se ingresa algo
    password = PasswordField('Nueva Contraseña (dejar en blanco para no cambiar)', validators=[Optional(), Length(min=6)])
    password2 = PasswordField(
        'Repetir Nueva Contraseña', validators=[EqualTo('password', message='Las contraseñas deben coincidir.')])
    is_admin = BooleanField('Es Administrador')
    submit = SubmitField('Guardar Cambios')

    # Necesitamos el usuario original para validar el username
    def __init__(self, original_username, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    # Validación de username adaptada: permite mantener el original
    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(db.select(User).where(User.username == username.data))
            if user is not None:
                raise ValidationError('Este nombre de usuario ya está en uso. Por favor, elige otro.')

