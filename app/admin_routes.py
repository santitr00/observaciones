# app/admin_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, abort, session
from app import db
# Quitar AssignUserForm
from app.forms import EditUserForm, AdminCreateUserForm
# Añadir UserPuestoAssignment
from app.models import User, Observation, UserPuestoAssignment, BARRIOS, PUESTOS
from flask_login import current_user, login_required
from sqlalchemy import func, and_
from functools import wraps

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorador admin_required (sin cambios)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_barrio = session.get('current_barrio')
        if not current_user.is_authenticated or not current_user.is_admin or not current_barrio:
            if current_user.is_authenticated and current_user.is_admin:
                 flash('Selecciona un barrio para administrar.', 'info'); return redirect(url_for('main.select_barrio'))
            abort(403)
        if current_user.barrio != current_barrio:
             flash(f'Tu cuenta de admin no corresponde al barrio {current_barrio}.', 'warning')
             return redirect(url_for('main.logout'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta para listar usuarios
@bp.route('/users')
@login_required
@admin_required
def list_users():
    current_barrio = session['current_barrio']
    users = db.session.scalars(db.select(User).where(User.barrio == current_barrio).order_by(User.nombre_completo)).all()
    create_form = AdminCreateUserForm(current_barrio=current_barrio)
    return render_template('admin/users.html',
                           title=f'Admin Usuarios ({current_barrio})',
                           users=users, create_form=create_form, current_barrio=current_barrio, UserPuestoAssignment=UserPuestoAssignment)

# Ruta para crear usuario 
@bp.route('/user/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    current_barrio = session['current_barrio']
    create_form = AdminCreateUserForm(current_barrio=current_barrio)
    if create_form.validate_on_submit():
        print(f"DEBUG: Formulario validado. DNI: {create_form.dni.data}, Puestos: {create_form.puestos.data}")
        user = User(
            dni=create_form.dni.data,
            nombre_completo=create_form.nombre_completo.data,
            email=create_form.email.data or None,
            barrio=current_barrio,
            is_admin=create_form.is_admin.data
            # Ya no se asigna 'zona' directamente a User
        )
        user.set_password(create_form.password.data)
        db.session.add(user)
        try:
            db.session.flush() # Obtener user.id
            for puesto_nombre in create_form.puestos.data:
                assignment = UserPuestoAssignment(user_id=user.id, barrio=current_barrio, puesto=puesto_nombre, )
                db.session.add(assignment)
            db.session.commit()
            print(f"DEBUG: Usuario {user.dni} y asignaciones commiteados.")
            flash(f'Usuario DNI {user.dni} creado y asignado a puestos en {current_barrio}.', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
             db.session.rollback()
             # ... (manejo de errores existente) ...
             # print(f"DEBUG: Usuario {user.dni} y asignaciones no commiteados.")
             if 'UNIQUE constraint failed: uq_dni_barrio' in str(e): flash(f'Error: El DNI {create_form.dni.data} ya existe en {current_barrio}.', 'danger')
             elif 'UNIQUE constraint failed: user.email' in str(e): flash('Error: El email ingresado ya existe.', 'danger')
             else: flash(f'Error al crear usuario o asignaciones: {e}', 'danger')
             users = db.session.scalars(db.select(User).where(User.barrio == current_barrio).order_by(User.nombre_completo)).all()
             return render_template('admin/users.html', title=f'Admin Usuarios ({current_barrio})', users=users, create_form=create_form, current_barrio=current_barrio, UserPuestoAssignment=UserPuestoAssignment)
    else:
        # print(f"DEBUG: Falló la validación del formulario. Errores: {create_form.errors}") # DEBUG
        # flash('Por favor, corrige los errores en el formulario de creación.', 'warning')
        for fieldName, errorMessages in create_form.errors.items():
            try: label = getattr(create_form, fieldName).label.text
            except AttributeError: label = fieldName.replace('_', ' ').title()
            # for err in errorMessages: print(f"Error en '{label}': {err}", "danger")
        users = db.session.scalars(db.select(User).where(User.barrio == current_barrio).order_by(User.nombre_completo)).all()


    return render_template('admin/users.html', title=f'Admin Usuarios ({current_barrio}) - Errores', users=users, create_form=create_form, current_barrio=current_barrio, UserPuestoAssignment=UserPuestoAssignment)


# Ruta para editar usuario (Modificada para editar DNI, Nombre, Email y Puestos)
@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    current_barrio_admin = session['current_barrio']
    user_to_edit = db.session.scalar(db.select(User).where(User.id == user_id, User.barrio == current_barrio_admin))
    if user_to_edit is None:
        flash('Usuario no encontrado o no pertenece a este barrio.', 'danger')
        return redirect(url_for('admin.list_users'))

    form = EditUserForm(user_to_edit=user_to_edit) # Pasar usuario para validación

    if form.validate_on_submit():
        user_to_edit.dni = form.dni.data
        user_to_edit.nombre_completo = form.nombre_completo.data
        user_to_edit.email = form.email.data or None
        user_to_edit.is_admin = form.is_admin.data # Permiso de admin para este barrio/user
        if form.password.data:
             user_to_edit.set_password(form.password.data)

        # Gestionar Puestos Asignados
        # 1. Borrar asignaciones existentes para este usuario en este barrio
        UserPuestoAssignment.query.filter_by(user_id=user_to_edit.id, barrio=current_barrio_admin).delete()
        # 2. Crear nuevas asignaciones basadas en el checklist
        for puesto_nombre in form.puestos.data:
            assignment = UserPuestoAssignment(user_id=user_to_edit.id, barrio=current_barrio_admin, puesto=puesto_nombre, )
            db.session.add(assignment)

        try:
            db.session.commit()
            flash(f'Usuario DNI {user_to_edit.dni} actualizado correctamente.', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
             db.session.rollback()
             # ... (manejo de errores existente) ...
             if 'UNIQUE constraint failed: uq_dni_barrio' in str(e): flash(f'Error: El DNI {form.dni.data} ya existe en {current_barrio_admin}.', 'danger')
             elif 'UNIQUE constraint failed: user.email' in str(e): flash('Error: El email ingresado ya existe para otro usuario.', 'danger')
             else: flash(f'Error al actualizar usuario: {e}', 'danger')
    elif request.method == 'GET':
        form.dni.data = user_to_edit.dni
        form.nombre_completo.data = user_to_edit.nombre_completo
        form.email.data = user_to_edit.email
        form.is_admin.data = user_to_edit.is_admin
        # Precargar los puestos asignados
        assigned_puestos = [assign.puesto for assign in user_to_edit.puestos_asignados.filter_by(barrio=current_barrio_admin).all()]
        form.puestos.data = assigned_puestos


    return render_template('admin/edit_user.html',
                           title=f'Editar Usuario ({current_barrio_admin})',
                           form=form, user_to_edit=user_to_edit, current_barrio=current_barrio_admin, UserPuestoAssignment=UserPuestoAssignment)


# Ruta para eliminar usuario (Modificada para borrar UserPuestoAssignment)
@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    current_barrio = session['current_barrio']
    user_to_delete = db.session.scalar(db.select(User).where(User.id == user_id, User.barrio == current_barrio))
    if user_to_delete is None: flash('Usuario no encontrado o no pertenece a este barrio.', 'danger'); return redirect(url_for('admin.list_users'))
    if user_to_delete.id == current_user.id: flash('No puedes eliminar tu propia cuenta.', 'danger'); return redirect(url_for('admin.list_users'))
    admin_count = db.session.scalar(db.select(func.count(User.id)).where(User.is_admin == True, User.barrio == current_barrio))
    if user_to_delete.is_admin and admin_count <= 1: flash(f'No puedes eliminar al último administrador de {current_barrio}.', 'danger'); return redirect(url_for('admin.list_users'))
    observation_count = user_to_delete.observations.count() # Observaciones globales
    if observation_count > 0: flash(f'No se puede eliminar al usuario DNI {user_to_delete.dni} porque tiene {observation_count} observaciones registradas.', 'danger'); return redirect(url_for('admin.list_users'))

    dni_deleted = user_to_delete.dni
    try:
        # Las asignaciones de puestos se borran por cascade="all, delete-orphan" en la relación User.puestos_asignados
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'Usuario DNI {dni_deleted} eliminado correctamente de {current_barrio}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {e}', 'danger')
    return redirect(url_for('admin.list_users'))


# --- Rutas manage_assignments y delete_assignment ELIMINADAS ---




















    




















    