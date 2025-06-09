# app/main_routes.py
import os
from flask import (Blueprint, render_template, flash, redirect, url_for,
                   request, current_app, abort, session, send_from_directory, make_response)
from app import db
# Quitar AssignUserForm
from app.forms import (LoginForm, ObservationForm, SearchForm,
                       ChangePasswordForm)
# Importar PUESTOS
from app.models import User, Observation, PUESTOS, BARRIOS, UserPuestoAssignment
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timezone, date, time
import pytz
from sqlalchemy import or_, func, desc, and_
from werkzeug.utils import secure_filename
import uuid
from weasyprint import HTML


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

PREDEFINED_BODY_TEXTS = {
    "INICIO JORNADA": "Recibo la guardia al tanto de las novedades que anteceden y con el puesto laboral en condiciones. ",
    "FIN JORNADA": "Se entrego la guardia con las novedades que anteceden y el puesto laboral en condiciones. ",
    "INICIO CORTE DE LUZ": "Se produce un corte de energía eléctrica, sin previo aviso. Los grupos electrógenos inician correctamente. ",
    "FIN CORTE DE LUZ": "Se restablece el servicio eléctrico de EPE. ",
}
# Ruta Index (Modificada)
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    current_barrio = session.get('current_barrio')
    if not current_barrio:
        flash('Error de sesión. Por favor, inicia sesión de nuevo.', 'danger')
        return redirect(url_for('main.logout'))

    # Obtener los nombres de los puestos a los que el usuario está ASIGNADO en este barrio.
    # Esta lista determina DÓNDE PUEDE REGISTRAR (editar) actas.
    puestos_asignados_al_usuario_en_barrio = current_user.get_puestos_asignados_en_barrio(current_barrio)

    # Determinar qué puestos se mostrarán en el menú desplegable (DÓNDE PUEDE VER).
    # Si el usuario tiene el permiso 'can_view_all_puestos', verá TODOS los puestos.
    # De lo contrario, solo verá los puestos a los que está asignado.
    if current_user.can_view_all_puestos:
        available_puestos_for_menu = PUESTOS
    else:
        available_puestos_for_menu = puestos_asignados_al_usuario_en_barrio

    # Si después de aplicar la lógica de visualización, no hay puestos disponibles para el usuario,
    # se le informa y se le muestra una página de índice sin contenido.
    if not available_puestos_for_menu:
        return render_template('index.html',
                               title=f'Libro: {current_barrio} - Sin Acceso',
                               obs_form=None, # Deshabilita el formulario de observación
                               search_form=None, # Deshabilita el formulario de búsqueda
                               observations=[], # No hay observaciones que mostrar
                               current_barrio=current_barrio,
                               target_puesto="N/A", # No hay puesto objetivo válido
                               available_puestos_for_menu=[], # El menú estará vacío o no se mostrará
                               can_register_in_target_puesto=False, # No puede registrar en ningún puesto
                               search_query="",
                               predefined_body_texts={})


    # Determinar el puesto actual a mostrar.
    # Se toma el puesto de la URL o el primer puesto disponible para el usuario como predeterminado.
    default_puesto_display = available_puestos_for_menu[0]
    requested_puesto = request.args.get('puesto', default=default_puesto_display, type=str)

    # El puesto objetivo es el solicitado si el usuario tiene permiso para VERLO.
    # De lo contrario, se redirige al puesto por defecto que sí puede ver.
    if requested_puesto in available_puestos_for_menu:
        target_puesto = requested_puesto
    else:
        target_puesto = default_puesto_display
        if requested_puesto != default_puesto_display: # Evitar mensaje si el default ya es el solicitado
             flash(f'No tienes permiso para ver el libro de actas del puesto "{requested_puesto}". Mostrando puesto por defecto: "{default_puesto_display}".', 'warning')

    # Determinar si el usuario PUEDE REGISTRAR ACTAS en el puesto actualmente visualizado (`target_puesto`).
    # Esto sigue basándose EXCLUSIVAMENTE en si el puesto está en sus asignaciones directas.
    can_register_in_target_puesto = target_puesto in puestos_asignados_al_usuario_en_barrio

    obs_form = ObservationForm()
    if request.method == 'GET' and not obs_form.observation_time.data and not obs_form.observation_date.data:
        try:
            local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            now_local = datetime.now(local_tz)
            obs_form.observation_date.data = now_local.date()
            obs_form.observation_time.data = now_local.time().replace(second=0, microsecond=0)
        except Exception as e: current_app.logger.error(f"Error setting default datetime: {e}")

    search_form = SearchForm(request.args, meta={'csrf': False})
    query = request.args.get('query', '').strip()
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    if query: search_form.query.data = query
    if start_date_str:
        try: search_form.start_date.data = date.fromisoformat(start_date_str)
        except ValueError: flash('Formato de fecha "desde" inválido.', 'warning')
    if end_date_str:
        try: search_form.end_date.data = date.fromisoformat(end_date_str)
        except ValueError: flash('Formato de fecha "hasta" inválido.', 'warning')

    # Procesar Registro de Observación
    if obs_form.validate_on_submit() and request.method == 'POST':
        # --- Validar si puede registrar en este puesto ---
        if not can_register_in_target_puesto:
             flash(f'No tienes permiso para registrar actas en el puesto {target_puesto}.', 'danger')
        # --------------------------------------------
        else:
            filename = None
            file = obs_form.attachment.data
            if file:
                try:
                    filename = unique_filename(file.filename)
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(upload_path)
                    flash('¡Acta registrada con éxito!', 'success')
                except Exception as e:
                     flash(f'Error al guardar el archivo adjunto: {e}', 'danger'); filename = None
            observation = Observation(
                classification=obs_form.classification.data, body=obs_form.body.data,
                observation_date=obs_form.observation_date.data, observation_time=obs_form.observation_time.data,
                author=current_user, barrio=current_barrio, zona=target_puesto, filename=filename
            )
            db.session.add(observation); db.session.commit()
            if observation.classification == "FIN JORNADA":
                # Guardar el nombre del usuario para el mensaje flash antes de cerrar sesión
                nombre_usuario_actual = current_user.nombre_completo 
                
                # Limpiar datos de sesión relevantes y cerrar la sesión del usuario
                session.pop('current_barrio', None) # Elimina el barrio actual de la sesión
                logout_user() # Cierra la sesión del usuario de Flask-Login
                
                # Mensaje flash informando al usuario
                flash(f'FIN DE JORNADA registrado por {nombre_usuario_actual}. Tu sesión ha sido cerrada.', 'info')
                # Redirigir a la página de selección de barrio (o login)
                return redirect(url_for('main.select_barrio')) 
            else:
                # Si no es "FIN JORNADA", mostrar mensaje de éxito normal
                flash('¡Acta registrada con éxito!', 'success')
                return redirect(url_for('main.index', puesto=target_puesto))
    
    

    # Obtener Observaciones
    observations = []
    # Solo buscar observaciones si el target_puesto es válido y está en la lista de los que el usuario puede ver
    if target_puesto and target_puesto in available_puestos_for_menu:
        observations_query = db.select(Observation).where(Observation.barrio == current_barrio, Observation.zona == target_puesto)
        if query:
            search_term = f"%{query}%"
            observations_query = observations_query.where(or_(Observation.classification.ilike(search_term), Observation.body.ilike(search_term)))
        if search_form.start_date.data:
             observations_query = observations_query.where(Observation.observation_date >= search_form.start_date.data)
        if search_form.end_date.data:
             observations_query = observations_query.where(Observation.observation_date <= search_form.end_date.data)
        observations = db.session.scalars(observations_query.order_by(Observation.observation_date.desc(), Observation.observation_time.desc())).all()

    # available_puestos_for_menu ya se determinó arriba con la lógica de 'can_view_all_puestos'

    return render_template('index.html',
                           title=f'Libro: {current_barrio} - {target_puesto}',
                           obs_form=obs_form,
                           search_form=search_form,
                           observations=observations,
                           current_barrio=current_barrio,
                           target_puesto=target_puesto,
                           available_puestos_for_menu=available_puestos_for_menu, # Se pasa la lista ya filtrada
                           can_register_in_target_puesto=can_register_in_target_puesto, # Para habilitar/deshabilitar form
                           search_query=query,
                           predefined_body_texts=PREDEFINED_BODY_TEXTS)



@bp.route('/libro_actas/pdf')
@login_required
def download_libro_actas_pdf():
    current_barrio = session.get('current_barrio')
    if not current_barrio:
        flash('Error de sesión.', 'danger')
        return redirect(url_for('main.logout'))

    # Obtener parámetros de filtro de la URL (los mismos que usa index)
    requested_puesto = request.args.get('puesto', PUESTOS[0] if PUESTOS else 'Default', type=str) # Mantener como requested
    query = request.args.get('query', '').strip()
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    # Validar que el usuario tenga permisos para descargar PDF de este puesto
    puestos_visibles_para_usuario = current_user.get_puestos_asignados_en_barrio(current_barrio) #
    if requested_puesto not in puestos_visibles_para_usuario: #
        flash(f'No tienes permiso para descargar el PDF del puesto "{requested_puesto}".', 'danger') #
        return redirect(url_for('main.index')) #

    target_puesto = requested_puesto # Si pasó la validación, el requested_puesto es el target_puesto válido

    # Obtener Actas Filtradas (misma lógica que en index)
    observations_query = db.select(Observation).where(
        Observation.barrio == current_barrio,
        Observation.zona == target_puesto
    )
    if query:
        search_term = f"%{query}%"
        observations_query = observations_query.where(or_(Observation.classification.ilike(search_term), Observation.body.ilike(search_term)))

    start_date_obj = None
    end_date_obj = None
    if start_date_str:
        try: start_date_obj = date.fromisoformat(start_date_str)
        except ValueError: flash('Fecha "desde" inválida.', 'warning')
    if end_date_str:
        try: end_date_obj = date.fromisoformat(end_date_str)
        except ValueError: flash('Fecha "hasta" inválido.', 'warning')

    if start_date_obj:
         observations_query = observations_query.where(Observation.observation_date >= start_date_obj)
    if end_date_obj:
         observations_query = observations_query.where(Observation.observation_date <= end_date_obj)

    observations = db.session.scalars(observations_query.order_by(Observation.observation_date.asc(), Observation.observation_time.asc())).all() # Ascendente para PDF

    # Renderizar la plantilla HTML específica para el PDF
    html_for_pdf = render_template('libro_actas_pdf.html',
                                   observations=observations,
                                   barrio=current_barrio,
                                   puesto=target_puesto,
                                   query=query,
                                   start_date_str=start_date_str, # Pasar strings para mostrar en PDF
                                   end_date_str=end_date_str,
                                   generation_time=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')))
    try:
        # Crear el PDF desde el HTML
        # font_config = FontConfiguration() # Para fuentes personalizadas (avanzado)
        pdf = HTML(string=html_for_pdf, base_url=request.base_url).write_pdf(
            # stylesheets=[CSS(string='@page { size: A4; margin: 0.5in; }')] # Estilos de página
        )

        # Crear la respuesta para descargar el PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="libro_actas_{current_barrio}_{target_puesto}_{date.today().isoformat()}.pdf"'
        return response
    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {e}")
        flash("Error al generar el PDF. Por favor, intente de nuevo.", "danger")
        # Redirigir a la página anterior o a index
        return redirect(request.referrer or url_for('main.index', puesto=target_puesto))


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