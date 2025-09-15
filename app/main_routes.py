# app/main_routes.py

from flask import (
    render_template, flash, redirect, url_for, request, session, Blueprint, g
)
from app import db
from app.forms import LoginForm, ObservationForm, SearchForm, ChangePasswordForm
from app.models import Usuario, Acta, Puesto, Barrio, PermisoPuesto
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime


main_bp = Blueprint('main', __name__)

# ---------------------------
# Helpers de contexto/acceso
# ---------------------------

def get_barrios_for_user(user):
    """Lista de Barrios a los que un usuario tiene acceso (por permisos o por ser admin)."""
    if user.rol.nombre == 'Super Admin':
        return db.session.scalars(db.select(Barrio).order_by(Barrio.nombre)).all()

    barrios = set()

    # Por permisos en puestos
    permisos_query = (
        db.select(Barrio)
        .join(Puesto)
        .join(PermisoPuesto)
        .where(PermisoPuesto.usuario_id == user.id)
        .distinct()
    )
    for b in db.session.scalars(permisos_query):
        barrios.add(b)

    # Por ser administrador de un barrio
    if user.barrio_admin:
        barrios.add(user.barrio_admin)

    return sorted(list(barrios), key=lambda b: b.nombre)


def ensure_barrio_access_or_403(user, barrio_id):
    """True si el usuario puede acceder al barrio_id actual."""
    if user.rol.nombre == 'Super Admin':
        return True
    return any(b.id == barrio_id for b in get_barrios_for_user(user))


@main_bp.before_app_request
def load_current_context():
    """Carga el contexto de barrio elegido en `g` para fácil acceso."""
    g.current_barrio_id = session.get('current_barrio_id')
    g.current_barrio_nombre = session.get('current_barrio_nombre')


# ---------------------------
# Rutas
# ---------------------------

# Ruta 1: Login (punto de entrada)
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(Usuario).where(Usuario.dni == form.dni.data))
        if user and user.verify_password(form.password.data):
            login_user(user, remember=True)

            barrios_accesibles = get_barrios_for_user(user)

            if len(barrios_accesibles) > 1:
                return redirect(url_for('main.select_context'))
            elif len(barrios_accesibles) == 1:
                barrio = list(barrios_accesibles)[0]
                session['current_barrio_id'] = barrio.id
                session['current_barrio_nombre'] = barrio.nombre
                return redirect(url_for('main.index'))
            else:
                # Sin barrios/puestos asignados
                logout_user()
                flash('No tienes ningún barrio o puesto asignado.', 'danger')
                return redirect(url_for('main.login'))

        flash('DNI o Contraseña incorrectos.', 'danger')
    return render_template('login.html', title='Iniciar Sesión', form=form)


# Ruta 2: Selector de Contexto (si el usuario tiene >1 barrio)
@main_bp.route('/select_context', methods=['GET', 'POST'])
@login_required
def select_context():
    barrios = get_barrios_for_user(current_user)

    # Si tiene 0 o 1 barrios (y no es Super Admin), resolvemos automáticamente
    if current_user.rol.nombre != 'Super Admin':
        if len(barrios) == 0:
            flash('No tienes ningún barrio asignado.', 'danger')
            return redirect(url_for('main.logout'))
        if len(barrios) == 1:
            b = barrios[0]
            session['current_barrio_id'] = b.id
            session['current_barrio_nombre'] = b.nombre
            return redirect(url_for('main.index'))

    # Selección explícita
    if request.method == 'POST':
        barrio_id = request.form.get('barrio', type=int)
        barrio_sel = db.session.get(Barrio, barrio_id)
        if barrio_sel and any(b.id == barrio_sel.id for b in barrios):
            session['current_barrio_id'] = barrio_sel.id
            session['current_barrio_nombre'] = barrio_sel.nombre
            return redirect(url_for('main.index'))
        flash('Selección de barrio inválida.', 'danger')

    return render_template('select_context.html', title='Seleccionar Contexto', barrios=barrios)


# Ruta 3: Index (home del barrio)
@main_bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    barrio_id = session.get('current_barrio_id')
    barrio_nombre = session.get('current_barrio_nombre')
    if not barrio_id:
        return redirect(url_for('main.select_context'))

    # Guardas de acceso...
    if not ensure_barrio_access_or_403(current_user, barrio_id):
        flash('No tenés acceso a este barrio.', 'danger')
        return redirect(url_for('main.select_context'))

    # Puestos visibles y editables
    if current_user.rol.nombre == 'Super Admin' or (
        current_user.rol.nombre == 'Administrador' and current_user.barrio_admin_id == barrio_id
    ):
        puestos_visibles = db.session.scalars(
            db.select(Puesto).where(Puesto.barrio_id == barrio_id).order_by(Puesto.nombre)
        ).all()
    else:
        puestos_visibles = [
            p.puesto for p in current_user.permisos
            if p.puede_ver and p.puesto.barrio_id == barrio_id
        ]

    if not puestos_visibles:
        return render_template('index.html', no_puestos=True, barrio_actual=barrio_nombre)

    target_puesto_id = request.args.get('puesto_id', puestos_visibles[0].id, type=int)
    target_puesto = db.session.get(Puesto, target_puesto_id) or puestos_visibles[0]
    if target_puesto not in puestos_visibles:
        target_puesto = puestos_visibles[0]

    puestos_editables = [
        p.puesto for p in current_user.permisos
        if p.puede_editar and p.puesto.barrio_id == barrio_id
    ]
    is_admin_of_current = (
        current_user.rol.nombre == 'Super Admin' or
        (current_user.rol.nombre == 'Administrador' and current_user.barrio_admin_id == barrio_id)
    )
    can_register_in_target_puesto = is_admin_of_current or any(
        p.id == target_puesto.id for p in puestos_editables
    )

    # Construir SIEMPRE el form con choices válidos (antes de validar)
    obs_form = ObservationForm(puestos_registrables=puestos_editables)
    search_form = SearchForm(request.args)

    # Opcional: preseleccionar primer puesto válido en GET
    if request.method == 'GET' and puestos_editables:
        if obs_form.puesto.data in (None, -1):
            obs_form.puesto.data = puestos_editables[0].id

    # --- POST de alta de acta ---
    if request.method == 'POST' and 'submit_obs' in request.form:
        if not can_register_in_target_puesto:
            flash('No tenés permiso para registrar en este puesto.', 'danger')
            return redirect(url_for('main.index', puesto_id=target_puesto.id))

        if obs_form.validate():
            puesto_id_form = obs_form.puesto.data
            puesto_form = db.session.get(Puesto, puesto_id_form)
            if (not puesto_form) or (puesto_form.barrio_id != barrio_id):
                flash('Puesto inválido.', 'danger')
                return redirect(url_for('main.index', puesto_id=target_puesto.id))

            nueva = Acta(
                puesto_id=puesto_form.id,
                usuario_id=current_user.id,
                clasificacion=obs_form.classification.data,
                cuerpo=obs_form.body.data
            )
            # Fecha/hora del evento si existen columnas
            if hasattr(Acta, 'fecha_evento') and hasattr(Acta, 'hora_evento'):
                nueva.fecha_evento = obs_form.observation_date.data
                nueva.hora_evento = obs_form.observation_time.data
            elif hasattr(Acta, 'fecha_hora_evento'):
                nueva.fecha_hora_evento = datetime.combine(
                    obs_form.observation_date.data, obs_form.observation_time.data
                )

            db.session.add(nueva)
            db.session.commit()
            flash('Acta registrada correctamente.', 'success')
            return redirect(url_for('main.index', puesto_id=puesto_form.id))
        else:
            # Mostrar exactamente qué campos fallaron
            for campo, errores in obs_form.errors.items():
                for err in errores:
                    flash(f'Error en {campo}: {err}', 'danger')

    # --- GET: listados + paginación ---
    page = request.args.get('page', 1, type=int)
    actas_query = db.select(Acta).where(Acta.puesto_id == target_puesto.id)
    if hasattr(Acta, 'fecha_creacion'):
        actas_query = actas_query.order_by(Acta.fecha_creacion.desc())
    pagination = db.paginate(actas_query, page=page, per_page=15, error_out=False)
    actas = pagination.items

    return render_template(
        'index.html',
        obs_form=obs_form,
        search_form=search_form,
        actas=actas,
        pagination=pagination,
        barrio_actual=barrio_nombre,
        target_puesto=target_puesto,
        puestos_visibles=puestos_visibles,
        can_register_in_target_puesto=can_register_in_target_puesto,
        predefined_body_texts={}
    )


# Ruta 4: Logout
@main_bp.route('/logout')
@login_required
def logout():
    barrio_nombre = session.get('current_barrio_nombre', 'N/A')
    logout_user()
    # limpiar contexto propio
    session.pop('current_barrio_id', None)
    session.pop('current_barrio_nombre', None)
    flash(f'Has cerrado sesión en {barrio_nombre}.', 'info')
    return redirect(url_for('main.login'))
