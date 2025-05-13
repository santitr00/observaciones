# app/routes.py
from flask import render_template, flash, redirect, url_for, request, current_app, abort
from app import db
from app.forms import LoginForm, ObservationForm, RegistrationForm, SearchForm, EditUserForm
# Importar modelos y listas globales
from app.models import User, Observation, Jornada, BARRIOS, ZONAS
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timezone
from sqlalchemy import or_, func, desc
from functools import wraps

# --- Decorador admin_required (sin cambios) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Ruta Index (Modificada para ver otras zonas del mismo barrio) ---
@current_app.route('/', methods=['GET', 'POST'])
@current_app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # --- Determinar Barrio y Zona a Mostrar ---
    target_barrio = current_user.barrio # Siempre el barrio del usuario logueado
    # Obtener la zona solicitada de los argumentos GET, si no, usar la del usuario
    requested_zona = request.args.get('zona', default=current_user.zona, type=str)

    # Validar que la zona solicitada sea válida (esté en la lista ZONAS)
    if requested_zona in ZONAS:
        target_zona = requested_zona
    else:
        # Si la zona no es válida, volver a la del usuario y mostrar advertencia (opcional)
        target_zona = current_user.zona
        if requested_zona != current_user.zona:
             flash(f'Zona "{requested_zona}" no válida. Mostrando tu zona por defecto.', 'warning')

    # Determinar si el usuario está viendo su propia zona o la de otro
    viewing_own_zona = (target_zona == current_user.zona)

    # --- Formularios ---
    # El formulario de observación solo se procesa si está viendo su propia zona
    obs_form = ObservationForm() if viewing_own_zona else None
    search_form = SearchForm(request.args) # Pasar args para búsqueda GET
    query = request.args.get('query', '').strip()
    if query: search_form.query.data = query

    # --- Procesar Registro de Observación (Solo si es POST, viendo propia zona y form es válido) ---
    if viewing_own_zona and obs_form and obs_form.validate_on_submit() and request.method == 'POST':
        # Buscar jornada activa para SU barrio/zona para enlazar la observación
        active_jornada_propia = db.session.scalar(
            db.select(Jornada).where(
                Jornada.barrio == current_user.barrio,
                Jornada.zona == current_user.zona,
                Jornada.end_time == None
            )
        )
        if not active_jornada_propia:
            flash('No puedes registrar una observación si tu jornada no está activa.', 'danger')
        else:
            observation = Observation(
                classification=obs_form.classification.data,
                body=obs_form.body.data,
                observation_time=obs_form.observation_time.data,
                author=current_user,
                barrio=current_user.barrio, # La observación siempre es del barrio/zona del autor
                zona=current_user.zona,
                jornada_id=active_jornada_propia.id # Enlazar con SU jornada activa
            )
            db.session.add(observation)
            db.session.commit()
            flash('¡Observación registrada con éxito!', 'success')
            # Redirigir a su propia zona después de registrar
            return redirect(url_for('index', zona=current_user.zona))


    # --- Lógica de Jornada (Para la ZONA que se está viendo) ---
    last_jornada_target = db.session.scalar(
        db.select(Jornada).where(
            Jornada.barrio == target_barrio, # Usar target_barrio
            Jornada.zona == target_zona     # Usar target_zona
        ).order_by(Jornada.start_time.desc())
    )

    active_jornada_target = None
    jornada_to_verify_target = None # Jornada de la zona vista que necesita verificación

    if last_jornada_target and last_jornada_target.is_active():
        active_jornada_target = last_jornada_target
    # OJO: La verificación solo la puede hacer alguien de ESA zona al iniciar SU jornada.
    # No mostraremos botón de verificar al ver otra zona.
    # elif last_jornada_target and not last_jornada_target.is_active() and not last_jornada_target.verified_by_user_id:
    #     jornada_to_verify_target = last_jornada_target


    # --- Obtener Observaciones (Filtradas por Barrio y Zona SELECCIONADA) ---
    observations_query = db.select(Observation).where(
        Observation.barrio == target_barrio, # Usar target_barrio
        Observation.zona == target_zona     # Usar target_zona
    ).order_by(Observation.timestamp.desc())

    if query:
        search_term = f"%{query}%"
        observations_query = observations_query.where(
            or_(
                Observation.classification.ilike(search_term),
                Observation.body.ilike(search_term)
            )
        )

    observations = db.session.scalars(observations_query).all()

    # Obtener la lista de zonas disponibles en el barrio del usuario para el menú
    available_zonas = ZONAS # Por ahora, todas las zonas son potencialmente visibles

    # Renderizar la plantilla
    return render_template('index.html',
                           title=f'Libro: {target_barrio} - {target_zona}', # Mostrar barrio/zona vista
                           obs_form=obs_form, # Será None si no es la propia zona
                           search_form=search_form,
                           observations=observations,
                           current_barrio=current_user.barrio, # Barrio del usuario
                           current_zona=current_user.zona,   # Zona del usuario
                           target_zona=target_zona,         # Zona que se está viendo
                           viewing_own_zona=viewing_own_zona, # True/False
                           available_zonas=available_zonas, # Lista de zonas para el menú
                           active_jornada=active_jornada_target, # Jornada de la zona vista
                           # jornada_to_verify=jornada_to_verify_target, # Ya no pasamos esto
                           search_query=query)

# --- Rutas start_jornada y end_jornada (Sin cambios, operan sobre la zona del usuario actual) ---
@current_app.route('/jornada/start', methods=['POST'])
@login_required
def start_jornada():
    # ... (código existente sin cambios) ...
    # Buscar si ya hay una jornada activa para SU barrio/zona
    existing_active = db.session.scalar(db.select(Jornada).where(Jornada.barrio == current_user.barrio, Jornada.zona == current_user.zona, Jornada.end_time == None))
    if existing_active: flash('Ya hay una jornada activa para tu barrio y zona.', 'warning'); return redirect(url_for('index'))
    # Buscar la última jornada cerrada de SU barrio/zona para verificarla
    last_closed = db.session.scalar(db.select(Jornada).where(Jornada.barrio == current_user.barrio, Jornada.zona == current_user.zona, Jornada.end_time != None).order_by(Jornada.end_time.desc()))
    if last_closed and not last_closed.verified_by_user_id:
        last_closed.verified_by_user_id = current_user.id
        last_closed.verified_time = datetime.now(timezone.utc)
        flash(f'Tu jornada anterior (ID: {last_closed.id}) verificada.', 'info')
    # Crear la nueva jornada para SU barrio/zona
    new_jornada = Jornada(barrio=current_user.barrio, zona=current_user.zona, start_user_id=current_user.id)
    db.session.add(new_jornada); db.session.commit()
    flash('Nueva jornada iniciada para tu puesto.', 'success')
    return redirect(url_for('index'))


@current_app.route('/jornada/end', methods=['POST'])
@login_required
def end_jornada():
    # ... (código existente sin cambios) ...
    # Buscar la jornada activa para SU barrio/zona
    active_jornada = db.session.scalar(db.select(Jornada).where(Jornada.barrio == current_user.barrio, Jornada.zona == current_user.zona, Jornada.end_time == None))
    if not active_jornada: flash('No hay ninguna jornada activa para finalizar en tu puesto.', 'warning'); return redirect(url_for('index'))
    if active_jornada.start_user_id != current_user.id and not current_user.is_admin: flash('Solo el usuario que inició la jornada o un administrador pueden finalizarla.', 'danger'); return redirect(url_for('index'))
    active_jornada.end_time = datetime.now(timezone.utc); active_jornada.end_user_id = current_user.id
    db.session.commit()
    flash(f'Tu jornada (ID: {active_jornada.id}) finalizada. Pendiente de verificación.', 'success')
    return redirect(url_for('index'))


# --- Rutas Login, Logout, Register, Admin (sin cambios recientes) ---
# ... (resto de las rutas: login, logout, register, list_users, edit_user, delete_user) ...



