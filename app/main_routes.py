# app/main_routes.py
import os
from flask import (Blueprint, render_template, flash, redirect, url_for,
                   request, current_app, abort, session, send_from_directory)
from app import db
# Quitar AssignUserForm
from app.forms import (LoginForm, ObservationForm, SearchForm,
                       ChangePasswordForm)
# Importar PUESTOS
from app.models import User, Observation, PUESTOS, BARRIOS # Quitar Jornada, Assignment
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timezone, date, time
import pytz
from sqlalchemy import or_, func, desc, and_
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('main', __name__)

def unique_filename(filename):
    ext = filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return secure_filename(unique_name)

# Ruta para Seleccionar Barrio
@bp.route('/select_barrio', methods=['GET', 'POST'])
def select_barrio():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        barrio = request.form.get('barrio')
        if barrio and barrio in BARRIOS:
            session['selected_barrio_for_login'] = barrio
            return redirect(url_for('main.login'))
        else: flash('Por favor, selecciona un barrio válido.', 'warning')
    return render_template('select_barrio.html', title='Seleccionar Barrio', barrios=BARRIOS)

# Ruta Login (Modificada para DNI)
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    selected_barrio = session.get('selected_barrio_for_login')
    if not selected_barrio:
        flash('Por favor, selecciona primero el barrio.', 'info')
        return redirect(url_for('main.select_barrio'))

    form = LoginForm()
    if form.validate_on_submit():
        # Buscar por DNI y Barrio
        user = db.session.scalar(
            db.select(User).where(
                and_(
                    User.dni == form.dni.data, # Usar DNI
                    User.barrio == selected_barrio
                )
            )
        )
        # Validar contraseña
        if user is None or not user.check_password(form.password.data):
            flash('DNI o Contraseña incorrectos para este barrio.', 'danger')
            # Mostrar login de nuevo con el error
        else:
            login_user(user)
            session['current_barrio'] = selected_barrio
            session.pop('selected_barrio_for_login', None)
            flash(f'Inicio de sesión exitoso para {selected_barrio}!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
                next_page = url_for('main.index')
            return redirect(next_page)

    return render_template('login.html', title=f'Login - {selected_barrio}', form=form, barrio=selected_barrio)

# Ruta Index (Modificada)
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    current_barrio = session.get('current_barrio')
    if not current_barrio:
        flash('Error de sesión. Por favor, inicia sesión de nuevo.', 'danger')
        return redirect(url_for('main.logout'))

    # La zona/puesto se selecciona desde la interfaz
    default_puesto = PUESTOS[0] if PUESTOS else 'Default'
    requested_puesto = request.args.get('puesto', default=default_puesto, type=str)
    target_puesto = requested_puesto if requested_puesto in PUESTOS else default_puesto
    if requested_puesto not in PUESTOS and requested_puesto != default_puesto:
         flash(f'Puesto "{requested_puesto}" no válido. Mostrando puesto por defecto.', 'warning')

    obs_form = ObservationForm()
    search_form = SearchForm(request.args, meta={'csrf': False})
    query = request.args.get('query', '').strip()
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    if query: search_form.query.data = query
    if start_date_str: search_form.start_date.data = date.fromisoformat(start_date_str)
    if end_date_str: search_form.end_date.data = date.fromisoformat(end_date_str)

    # Procesar Registro de Observación
    if obs_form.validate_on_submit() and request.method == 'POST':
        # Ya no necesitamos verificar asignación, el login valida el barrio
        filename = None
        file = obs_form.attachment.data
        if file:
            try:
                filename = unique_filename(file.filename)
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(upload_path)
            except Exception as e:
                 flash(f'Error al guardar el archivo adjunto: {e}', 'danger'); filename = None

        observation = Observation(
            classification=obs_form.classification.data,
            body=obs_form.body.data,
            observation_date=obs_form.observation_date.data, # Fecha obligatoria
            observation_time=obs_form.observation_time.data, # Hora obligatoria
            author=current_user,
            barrio=current_barrio,
            zona=target_puesto, # Usar el puesto seleccionado en la interfaz
            filename=filename
        )
        db.session.add(observation)
        db.session.commit()
        flash('¡Observación registrada con éxito!', 'success')
        return redirect(url_for('main.index', puesto=target_puesto)) # Mantener el puesto

    # Obtener Observaciones
    observations_query = db.select(Observation).where(
        Observation.barrio == current_barrio,
        Observation.zona == target_puesto # Filtrar por puesto seleccionado
    )
    if query:
        search_term = f"%{query}%"
        observations_query = observations_query.where(or_(Observation.classification.ilike(search_term), Observation.body.ilike(search_term)))
    if search_form.start_date.data:
         start_dt = datetime.combine(search_form.start_date.data, time.min).replace(tzinfo=timezone.utc)
         # Comparar con la fecha de la observación, no con timestamp de registro
         observations_query = observations_query.where(Observation.observation_date >= search_form.start_date.data)
    if search_form.end_date.data:
         end_dt = datetime.combine(search_form.end_date.data, time.max).replace(tzinfo=timezone.utc)
         # Comparar con la fecha de la observación
         observations_query = observations_query.where(Observation.observation_date <= search_form.end_date.data)

    # Ordenar por fecha y luego hora de la observación descendente
    observations = db.session.scalars(observations_query.order_by(
        Observation.observation_date.desc(),
        Observation.observation_time.desc()
    )).all()

    available_puestos = PUESTOS # Lista global de puestos

    return render_template('index.html',
                           title=f'Libro: {current_barrio} - {target_puesto}',
                           obs_form=obs_form,
                           search_form=search_form,
                           observations=observations,
                           current_barrio=current_barrio,
                           target_puesto=target_puesto, # Renombrar variable
                           available_puestos=available_puestos, # Renombrar variable
                           search_query=query)


# Ruta Logout
@bp.route('/logout')
def logout():
    session.pop('current_barrio', None)
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('main.select_barrio')) # Ir a selección de barrio


# Ruta para Cambiar Contraseña
@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data): flash('La contraseña actual es incorrecta.', 'danger')
        elif form.current_password.data == form.new_password.data: flash('La nueva contraseña no puede ser igual a la actual.', 'warning')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Tu contraseña ha sido actualizada.', 'success')
            return redirect(url_for('main.index'))
    return render_template('admin/change_password.html', title='Cambiar Contraseña', form=form)


# Ruta para Servir Archivos
@bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    try:
        # Añadir validación de seguridad: ¿Puede este usuario ver este archivo?
        # obs = db.session.scalar(db.select(Observation).where(Observation.filename == filename))
        # if not obs or obs.barrio != session.get('current_barrio'):
        #     abort(403) # O 404 para no dar pistas
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)










    