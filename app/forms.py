# app/forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, SelectField,
                   TextAreaField, TimeField, DateField, FileField, EmailField,
                   SelectMultipleField, BooleanField, widgets)
from wtforms.validators import (DataRequired, Length, Email, EqualTo,
                                ValidationError, Optional, Regexp, )
from flask_wtf.file import FileAllowed
from app.models import Usuario, Rol, Puesto, Barrio, Organizacion, Plan  # AHORA: Importamos los modelos correctos
from app import db
from datetime import date, timedelta

# --- Validador personalizado para fecha de observación (sin cambios) ---
def date_check(form, field):
    if field.data:
        today = date.today()
        if field.data > today:
            raise ValidationError("La fecha no puede ser futura.")
        # Opcional: Podrías querer eliminar o ajustar la siguiente restricción
        one_day_ago = today - timedelta(days=1)
        if field.data < one_day_ago:
            raise ValidationError("La fecha no puede ser anterior a ayer.")

# --- Widget para checklist (sin cambios) ---
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class CrearOrganizacionForm(FlaskForm):
    nombre_org = StringField('Nombre de la Organización (Ej: Consorcio Funes Hills)', validators=[DataRequired()])
    plan = SelectField('Plan de Suscripción', coerce=int, validators=[DataRequired()])
    barrio_a_gestionar = SelectField('Barrio Principal a Gestionar', coerce=int, validators=[DataRequired()])
    
    # Datos para el primer Admin de este barrio
    admin_dni = StringField('DNI del Admin del Barrio', validators=[DataRequired(), Length(min=7, max=8)])
    admin_nombre = StringField('Nombre Completo del Admin', validators=[DataRequired()])
    admin_email = EmailField('Email del Admin', validators=[DataRequired(), Email()])
    admin_password = PasswordField('Contraseña para el Admin', validators=[DataRequired(), Length(min=8)])
    
    submit = SubmitField('Crear Organización y Administrador')

    def __init__(self, *args, **kwargs):
        super(CrearOrganizacionForm, self).__init__(*args, **kwargs)
        # Poblar dinámicamente los campos de selección
        self.plan.choices = [(p.id, f'{p.nombre} - ${p.precio}/mes') for p in db.session.scalars(db.select(Plan)).all()]
        self.barrio_a_gestionar.choices = [(b.id, b.nombre) for b in db.session.scalars(db.select(Barrio)).all()]

    def validate_nombre_org(self, nombre_org):
        if db.session.scalar(db.select(Organizacion).where(Organizacion.nombre == nombre_org.data)):
            raise ValidationError('Ya existe una organización con este nombre.')

    def validate_admin_email(self, admin_email):
        if db.session.scalar(db.select(Usuario).where(Usuario.email == admin_email.data)):
            raise ValidationError('Este email ya está en uso por otro usuario.')

# --- Formulario de Login (sin cambios, ya estaba correcto) ---
class LoginForm(FlaskForm):
    dni = StringField('DNI', validators=[DataRequired(message="El DNI es obligatorio"), Regexp('^[0-9]+$', message='El DNI solo debe contener números.')])
    password = PasswordField('Contraseña', validators=[DataRequired(message='La contraseña es obligatoria.')])
    submit = SubmitField('Iniciar Sesión')

# --- Formulario de Acta (Refactorizado) ---
class ObservationForm(FlaskForm):
    classification_choices = [('', '-- SELECCIONE TIPO DE ACTA --'),
        ('INICIO JORNADA', 'INICIO JORNADA'),
        ('FIN JORNADA', 'FIN JORNADA'),
        ('CONSTANCIA', 'CONSTANCIA'),
        ('ORDEN', 'ORDEN'),
        ('INICIO CORTE DE LUZ', 'INICIO CORTE DE LUZ'),
        ('FIN CORTE DE LUZ', 'FIN CORTE DE LUZ')
    ]
    
    # AHORA: El puesto se selecciona de una lista dinámica
    puesto = SelectField('Puesto donde registrar', coerce=int, validators=[DataRequired(message="Debe seleccionar un puesto.")])
    
    classification = SelectField('Clasificación', choices=classification_choices, validators=[DataRequired(message="La clasificación es obligatoria.")])
    observation_date = DateField('Fecha del Evento', format='%Y-%m-%d', validators=[DataRequired(message="La fecha es obligatoria."), date_check], default=date.today)
    observation_time = TimeField('Hora del Evento', format='%H:%M', validators=[DataRequired(message="La hora es obligatoria.")])
    body = TextAreaField('Descripción', validators=[DataRequired(message="La descripción es obligatoria"), Length(min=5, max=2000)], render_kw={"rows": 4})
    attachment = FileField('Adjuntar Archivo (Opcional)', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'], '¡Solo imágenes o documentos!')])
    submit = SubmitField('Registrar Acta', name="submit_obs")

    def __init__(self, puestos_registrables=None, *args, **kwargs):
        super(ObservationForm, self).__init__(*args, **kwargs)
        # Los puestos se pueblan dinámicamente desde la ruta,
        # mostrando solo aquellos donde el usuario puede registrar.
        if puestos_registrables:
            self.puesto.choices = [(p.id, p.nombre) for p in puestos_registrables]
            self.puesto.choices.insert(0, (-1, '-- SELECCIONE PUESTO --'))
        else:
            self.puesto.choices = [(-1, '— SIN PUESTOS HABILITADOS —')]

    def validate_puesto(self, field):
        if field.data == -1:
            raise ValidationError("Debe seleccionar un puesto válido.")

# --- Formulario de Búsqueda (sin cambios, ya estaba correcto) ---
class SearchForm(FlaskForm):
    query = StringField('Buscar en Actas', validators=[Optional()])
    start_date = DateField('Desde Fecha', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('Hasta Fecha', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Buscar')

# --- Formulario para Crear Usuario (CORREGIDO) ---
# Renombrado de AdminCreateUserForm a un nombre más genérico.
class CreateUserForm(FlaskForm):
    dni = StringField('DNI', validators=[DataRequired(message="El DNI es obligatorio."), # Ahora obligatorio
        Regexp('^[0-9]+$', message='El DNI solo debe contener números. '),
        Length(min=8, max=8, message='El DNI debe tener exactamente 8 dígitos.')])
    nombre_completo = StringField('Nombre Completo', validators=[DataRequired(message='Es necesario crear el usuario con Nombre y Apellido.'), Length(max=128, message='El nombre no puede exceder los 128 caracteres.')])

    email = StringField('Email (Opcional)', validators=[Optional(), Email(message='Email inválido'), Length(max=120, message='El email no puede exceder los 120 caracteres.')])

    password = PasswordField('Contraseña', validators=[DataRequired(message='La contraseña es obligatoria.'), Length(min=6, message='La contraseña debe tener al menos 6 caracteres.'), 
        Regexp(r'.*[a-z]', message='La contraseña debe contener al menos una letra minúscula. '),
        Regexp(r'.*[A-Z]', message='La contraseña debe contener al menos una letra mayúscula. '),
        Regexp(r'.*[0-9]', message='La contraseña debe contener al menos un número.')])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(message='Es necesario repetir la contraseña.'), EqualTo('password', message='Las contraseñas deben coincidir.')])

    # Usamos SelectMultipleField para que el admin elija uno o más puestos.
    puestos = SelectMultipleField('Asignar a Puestos', coerce=int, validators=[DataRequired(message="Debe seleccionar al menos un puesto.")])
    
    # Checkboxes para definir los permisos sobre los puestos seleccionados.
    puede_ver = BooleanField('Permiso para VER en los puestos seleccionados', default=True)
    puede_editar = BooleanField('Permiso para EDITAR en los puestos seleccionados', default=False)

    submit = SubmitField('Crear Usuario')

    def __init__(self, barrio_id, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        # Llenamos dinámicamente las opciones del campo 'puestos' con los puestos
        # que pertenecen al barrio del administrador que está usando el formulario.
        self.puestos.choices = [
            (p.id, p.nombre) for p in 
            db.session.scalars(db.select(Puesto).where(Puesto.barrio_id == barrio_id).order_by(Puesto.nombre)).all()
        ]

    def validate_dni(self, dni):
        user = db.session.scalar(db.select(Usuario).where(Usuario.dni == dni.data))
        if user:
            raise ValidationError('Este DNI ya está registrado. Por favor, use uno diferente.')

    def validate_email(self, email):
        if email.data: # Solo valida si se ingresó un email
            user = db.session.scalar(db.select(Usuario).where(Usuario.email == email.data))
            if user:
                raise ValidationError('Este email ya está en uso. Por favor, use uno diferente.')

# --- Formulario para Editar Usuario (CORREGIDO) ---
class EditUserForm(FlaskForm):
    """
    Formulario para que un Admin de Barrio edite un usuario existente.
    """
    dni = StringField('DNI', validators=[DataRequired(), Length(min=7, max=10)])
    nombre_completo = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Email (Opcional)', validators=[Optional(), Email()])
    
    # Las contraseñas son opcionales. Solo se validan si se rellenan.
    password = PasswordField('Nueva Contraseña (dejar en blanco para no cambiar)', validators=[Optional(), Length(min=6)])
    password2 = PasswordField('Repetir Nueva Contraseña', validators=[Optional(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    
    puestos = SelectMultipleField('Puestos Asignados', coerce=int, validators=[DataRequired(message="Debe seleccionar al menos un puesto.")])
    puede_ver = BooleanField('Permiso para VER en los puestos seleccionados', default=True)
    puede_editar = BooleanField('Permiso para EDITAR (Registrar Actas) en los puestos seleccionados', default=False)
    submit = SubmitField('Guardar Cambios')

    def __init__(self, original_user, barrio_id, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
        # Llenamos las opciones de puestos igual que en el formulario de creación
        self.puestos.choices = [
            (p.id, p.nombre) for p in 
            db.session.scalars(db.select(Puesto).where(Puesto.barrio_id == barrio_id).order_by(Puesto.nombre)).all()
        ]

    def validate_dni(self, dni):
        # Solo valida si el DNI ha cambiado Y el nuevo DNI ya existe
        if dni.data != self.original_user.dni:
            user = db.session.scalar(db.select(Usuario).where(Usuario.dni == dni.data))
            if user:
                raise ValidationError('Este DNI ya está registrado para otro usuario.')

    def validate_email(self, email):
        # Solo valida si el email ha cambiado Y el nuevo email ya existe
        if email.data and email.data != self.original_user.email:
            user = db.session.scalar(db.select(Usuario).where(Usuario.email == email.data))
            if user:
                raise ValidationError('Este email ya está en uso por otro usuario.')

# --- Formulario para Cambiar Contraseña (sin cambios, ya estaba bien) ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña Actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        EqualTo('new_password2', message='Las contraseñas deben coincidir.')
    ])
    new_password2 = PasswordField('Repetir Nueva Contraseña', validators=[DataRequired()])
    submit = SubmitField('Cambiar Contraseña')

class SelectBarrioForm(FlaskForm):
    """Formulario para la página de selección de barrio."""
    barrio = SelectField('Selecciona un Barrio para Continuar', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Ingresar')

    def __init__(self, *args, **kwargs):
        super(SelectBarrioForm, self).__init__(*args, **kwargs)
        # Poblar las opciones del SelectField dinámicamente desde la base de datos
        self.barrio.choices = [(b.id, b.nombre) for b in db.session.scalars(db.select(Barrio).order_by(Barrio.nombre)).all()]


















    









