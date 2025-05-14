# app/forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, SelectField,
                   TextAreaField, BooleanField, TimeField, DateField,
                   FileField, EmailField, SelectMultipleField, widgets)
from wtforms.validators import (DataRequired, Length, Email, EqualTo,
                                ValidationError, Optional, Regexp, InputRequired) # Optional ya no se usa para DNI
from flask_wtf.file import FileAllowed
from app.models import User, BARRIOS, PUESTOS # Renombrado ZONAS a PUESTOS
from app import db
from sqlalchemy import and_
from datetime import date, timedelta

# --- Validador personalizado para fecha de observación ---
def date_check(form, field):
    if field.data:
        today = date.today()
        one_day_ago = today - timedelta(days=1)
        if field.data > today:
            raise ValidationError("La fecha no puede ser futura.")
        if field.data < one_day_ago:
            raise ValidationError("La fecha no puede ser anterior a ayer.")

# --- Validador personalizado para checklist (al menos uno) ---
def atleast_one(form, field):
    if not field.data:
        raise ValidationError('Debe seleccionar al menos un puesto.')

# --- Widget para checklist ---
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


# --- Formulario de Login (Usa DNI) ---
class LoginForm(FlaskForm):
    dni = StringField('DNI', validators=[DataRequired(message="El DNI es obligatorio"), Regexp('^[0-9]+$', message='El DNI solo debe contener números.')])
    password = PasswordField('Contraseña', validators=[DataRequired(message='La contraseña es obligatoria.')])
    submit = SubmitField('Iniciar Sesión')

# --- Formulario de Acta ---
class ObservationForm(FlaskForm):
    classification_choices = [('', '-- SELECCIONE TIPO DE ACTA --'),
        ('INICIO JORNADA', 'INICIO JORNADA'),
        ('FIN JORNADA', 'FIN JORNADA'),
        ('CONSTANCIA', 'CONSTANCIA'),
        ('ORDEN', 'ORDEN'),
        ('CAMBIO FECHA', 'CAMBIO FECHA'),
    ]
    classification = SelectField('Clasificación', choices=classification_choices, validators=[DataRequired(message="La clasificación es obligatoria.")])
    observation_date = DateField('Fecha del Evento', format='%Y-%m-%d', validators=[DataRequired(message="La fecha es obligatoria."), date_check])
    observation_time = TimeField('Hora del Evento (HH:MM)', format='%H:%M', validators=[DataRequired(message="La hora es obligatoria.")])
    body = TextAreaField('Descripción', validators=[DataRequired(message="ES obligatorio agregar una descripción"), Length(min=5, max=500)], render_kw={"rows": 4})
    attachment = FileField('Adjuntar Archivo (Opcional)', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'], '¡Solo imágenes o documentos!')])
    submit = SubmitField('Registrar Observación')

# --- Formulario de Búsqueda ---
class SearchForm(FlaskForm):
    query = StringField('Buscar en Obs.', validators=[Optional()])
    start_date = DateField('Desde Fecha', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('Hasta Fecha', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Buscar')

# --- Formulario para Editar Usuario (Admin - DNI Obligatorio y 8 dígitos) ---
class EditUserForm(FlaskForm):
    dni = StringField('DNI', validators=[
        DataRequired(message="El DNI es obligatorio."),
        Regexp('^[0-9]+$', message='El DNI solo debe contener números.'),
        Length(min=8, max=8, message='El DNI debe tener exactamente 8 dígitos.')
    ])
    nombre_completo = StringField('Nombre y Apellido', validators=[DataRequired(), Length(max=128)])
    email = EmailField('Email (Opcional)', validators=[Optional(), Length(max=120), Email()])
    # --- ASEGURARSE QUE ESTE CAMPO ESTÉ PRESENTE Y CORRECTO ---
    puestos = MultiCheckboxField(
        'Puestos Asignados',
        choices=[(p, p) for p in PUESTOS],
        validators= [Optional()]
    )
    # --------------------------------------------------------
    password = PasswordField('Nueva Contraseña (dejar en blanco para no cambiar)', validators=[Optional(), Length(min=8, message='La contraseña debe tener al menos 8 dígitos.')])
    password2 = PasswordField('Repetir Nueva Contraseña', validators=[EqualTo('password', message='Las contraseñas deben coincidir.')])
    is_admin = BooleanField('Es Administrador')
    submit = SubmitField('Guardar Cambios')

    def __init__(self, user_to_edit, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.user_to_edit = user_to_edit

    # Validaciones (dni, email) ...
    def validate_dni(self, dni):
        if dni.data != self.user_to_edit.dni:
            user = db.session.scalar(
                db.select(User).where(
                    and_(
                        User.dni == dni.data,
                        User.barrio == self.user_to_edit.barrio
                    )
                )
            )
            if user is not None:
                raise ValidationError(f'Este DNI ya está en uso para otro usuario en {self.user_to_edit.barrio}.')

    def validate_email(self, email):
        if email.data and email.data != self.user_to_edit.email:
            user = db.session.scalar(db.select(User).where(User.email == email.data))
            if user is not None:
                raise ValidationError('Este email ya está registrado para otro usuario.')

# --- Formulario para Crear Usuario (Admin - DNI Obligatorio y 8 dígitos) ---
class AdminCreateUserForm(FlaskForm):
    dni = StringField('DNI', validators=[
        DataRequired(message="El DNI es obligatorio."), # Ahora obligatorio
        Regexp('^[0-9]+$', message='El DNI solo debe contener números.'),
        Length(min=8, max=8, message='El DNI debe tener exactamente 8 dígitos.') # Exactamente 8
    ])
    nombre_completo = StringField('Nombre y Apellido', validators=[DataRequired(message='Es necesario crear el usuario con Nombre y Apellido.'), Length(max=128)])
    email = EmailField('Email (Opcional)', validators=[Optional(), Length(max=120), Email()])
    puestos = MultiCheckboxField('Puestos a Asignar', choices=[(p, p) for p in PUESTOS], validators= [Optional()]) 

    password = PasswordField('Contraseña', validators=[DataRequired(message='Es necesario crear el usuario con una contraseña.'), Length(min=8, message='La contraseña debe tener al menos 8 digitos.')])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(message='Es necesario completar este campo.'), EqualTo('password', message='Las contraseñas deben coincidir.')])
    is_admin = BooleanField('Es Administrador (en este barrio)')
    submit = SubmitField('Crear Usuario y Asignar Puestos')

    def __init__(self, current_barrio, *args, **kwargs):
        super(AdminCreateUserForm, self).__init__(*args, **kwargs)
        self.current_barrio = current_barrio

    # Validar que el DNI sea único DENTRO del barrio actual
    def validate_dni(self, dni):
        user = db.session.scalar(
            db.select(User).where(
                and_(
                    User.dni == dni.data,
                    User.barrio == self.current_barrio
                )
            )
        )
        if user is not None:
            raise ValidationError(f'Este DNI ya está en uso en {self.current_barrio}.')

    # Validar unicidad global de Email si se ingresó
    def validate_email(self, email):
        if email.data:
            user = db.session.scalar(db.select(User).where(User.email == email.data))
            if user is not None: raise ValidationError('Este email ya está registrado.')

# --- Formulario para Cambiar Contraseña (Usuario) ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña Actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Repetir Nueva Contraseña', validators=[DataRequired(), EqualTo('new_password', message='Las nuevas contraseñas deben coincidir.')])
    submit = SubmitField('Cambiar Contraseña')









