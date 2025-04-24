# app/routes.py
from flask import render_template, flash, redirect, url_for, request, current_app, abort
from app import db
from app.forms import LoginForm, ObservationForm, RegistrationForm, SearchForm, EditUserForm
from app.models import User, Observation
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime, timezone
from sqlalchemy import or_, func
from functools import wraps

# --- Decorador admin_required (sin cambios) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Ruta Index (Búsqueda Mejorada) ---
@current_app.route('/', methods=['GET', 'POST'])
@current_app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    obs_form = ObservationForm()
    search_form = SearchForm() # Instanciar siempre para mostrarla
    query = None # Inicializar query

    # --- Procesar Registro de Observación (Solo si es POST y es el form correcto) ---
    # Usamos 'obs_form.submit.data' para diferenciar del form de búsqueda si ambos fueran POST
    if obs_form.validate_on_submit() and request.method == 'POST':
         observation = Observation(
            classification=obs_form.classification.data,
            body=obs_form.body.data,
            author=current_user
        )
         db.session.add(observation)
         db.session.commit()
         flash('¡Observación registrada con éxito!', 'success')
         return redirect(url_for('index')) # Redirigir para limpiar form

    # --- Procesar Búsqueda (Si es GET y hay parámetro 'query') ---
    if request.method == 'GET':
        query = request.args.get('query', '').strip() # Obtener de URL, quitar espacios extra
        if query:
            # Poblar el campo del formulario para que muestre lo que se buscó
            search_form.query.data = query
            # Opcional: Mostrar un flash si se realizó una búsqueda
            # flash(f'Mostrando resultados para: "{query}"', 'info')
        else:
             # Si no hay query en URL, asegurarse que el campo esté vacío
             search_form.query.data = ''


    # --- Obtener Observaciones (Filtrar si hay 'query') ---
    observations_query = db.select(Observation).order_by(Observation.timestamp.desc())

    if query:
        # Aplicar filtro si 'query' tiene contenido
        search_term = f"%{query}%"
        observations_query = observations_query.where(
            or_(
                Observation.classification.ilike(search_term),
                Observation.body.ilike(search_term)
                # Podrías añadir búsqueda por autor si unes User:
                # db.select(Observation).join(User).where(or_(..., User.username.ilike(search_term)))
            )
        )

    observations = db.session.scalars(observations_query).all()

    # Renderizar la plantilla pasando ambos formularios y los datos
    return render_template('index.html',
                           title='Página Principal',
                           obs_form=obs_form,
                           search_form=search_form, # Pasar siempre el form de búsqueda
                           observations=observations,
                           search_query=query) # Pasar el término buscado (puede ser None o vacío)


# --- Rutas Login, Logout, Register, list_users, edit_user, delete_user (sin cambios recientes) ---
@current_app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o Contraseña incorrectos', 'danger'); return redirect(url_for('login'))
        login_user(user, remember=False)
        flash('¡Inicio de sesión exitoso!', 'success')
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'): next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Iniciar Sesión', form=form)

@current_app.route('/logout')
def logout():
    logout_user(); flash('Has cerrado sesión.', 'info'); return redirect(url_for('index'))

@current_app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data); user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash('¡Te has registrado correctamente! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registrar Usuario', form=form)

@current_app.route('/admin/users')
@login_required
@admin_required
def list_users():
    users = db.session.scalars(db.select(User).order_by(User.username)).all()
    return render_template('admin/users.html', title='Administrar Usuarios', users=users)

@current_app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_to_edit = db.session.get(User, user_id)
    if user_to_edit is None: flash('Usuario no encontrado.', 'danger'); return redirect(url_for('list_users'))
    form = EditUserForm(original_username=user_to_edit.username)
    if form.validate_on_submit():
        user_to_edit.username = form.username.data
        user_to_edit.is_admin = form.is_admin.data
        if form.password.data: user_to_edit.set_password(form.password.data)
        db.session.commit()
        flash(f'Usuario "{user_to_edit.username}" actualizado correctamente.', 'success')
        return redirect(url_for('list_users'))
    elif request.method == 'GET':
        form.username.data = user_to_edit.username
        form.is_admin.data = user_to_edit.is_admin
    return render_template('admin/edit_user.html', title='Editar Usuario', form=form, user_to_edit=user_to_edit)

@current_app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_to_delete = db.session.get(User, user_id)
    if user_to_delete is None: flash('Usuario no encontrado.', 'danger'); return redirect(url_for('list_users'))
    if user_to_delete.id == current_user.id: flash('No puedes eliminar tu propia cuenta de administrador.', 'danger'); return redirect(url_for('list_users'))
    admin_count = db.session.scalar(db.select(func.count(User.id)).where(User.is_admin == True))
    if user_to_delete.is_admin and admin_count <= 1: flash('No puedes eliminar al último administrador.', 'danger'); return redirect(url_for('list_users'))
    observation_count = user_to_delete.observations.count()
    if observation_count > 0: flash(f'No se puede eliminar al usuario "{user_to_delete.username}" porque tiene {observation_count} observaciones registradas.', 'danger'); return redirect(url_for('list_users'))
    username_deleted = user_to_delete.username
    db.session.delete(user_to_delete); db.session.commit()
    flash(f'Usuario "{username_deleted}" eliminado correctamente.', 'success')
    return redirect(url_for('list_users'))



