# app/admin_routes.py

from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from app import db
from app.forms import CreateUserForm, EditUserForm  # Usamos los formularios ya refactorizados
from app.models import Usuario, Rol, Puesto, Barrio, PermisoPuesto, Acta
from flask_login import current_user, login_required
from sqlalchemy import func
from functools import wraps


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        if not current_user.barrio_admin_id:
            flash('Tu cuenta de administrador no tiene un barrio asignado para gestionar.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    """
    Muestra una lista de usuarios DEL BARRIO que el admin gestiona
    y el formulario para crear uno nuevo.
    """
    admin_barrio_id = current_user.barrio_admin_id
    
    # Preparamos el formulario de creación para pasarlo a la plantilla.
    create_form = CreateUserForm(barrio_id=admin_barrio_id)

    # Consulta para obtener los usuarios que tienen al menos un permiso en un puesto de este barrio.
    puestos_del_barrio_ids = db.session.scalars(db.select(Puesto.id).where(Puesto.barrio_id == admin_barrio_id)).all()
    
    # Usamos la relación correcta: 'permisos'
    user_query = db.select(Usuario).join(Usuario.permisos).where(PermisoPuesto.puesto_id.in_(puestos_del_barrio_ids)).distinct()
    
    page = request.args.get('page', 1, type=int)
    pagination = db.paginate(user_query.order_by(Usuario.nombre_completo), page=page, per_page=15)
    users = pagination.items
    
    return render_template('admin/users.html', 
                           title=f'Usuarios de {current_user.barrio_admin.nombre}', 
                           users=users, 
                           pagination=pagination,
                           create_form=create_form,
                           current_barrio=current_user.barrio_admin.nombre)

@admin_bp.route('/user/create', methods=['POST']) # Solo acepta POST
@login_required
@admin_required
def create_user():
    """
    Procesa la creación de un usuario y lo asigna a puestos DENTRO del barrio del admin.
    """
    admin_barrio_id = current_user.barrio_admin_id
    form = CreateUserForm(barrio_id=admin_barrio_id)
    
    if form.validate_on_submit():
        # Obtenemos el rol 'Usuario' por defecto para los nuevos creados.
        rol_usuario = db.session.scalar(db.select(Rol).where(Rol.nombre == 'Usuario'))
        if not rol_usuario:
            # Fallback por si el rol no existe
            flash('Error crítico: El rol "Usuario" no se encuentra en la base de datos.', 'danger')
            return redirect(url_for('admin.list_users'))

        new_user = Usuario(
            dni=form.dni.data,
            nombre_completo=form.nombre_completo.data,
            email=form.email.data or None,
            rol_id=rol_usuario.id,
            organizacion_id=current_user.organizacion_id,
        )
        new_user.password = form.password.data
        db.session.add(new_user)
        
        # Iteramos sobre los puestos seleccionados en el formulario
        for puesto_id in form.puestos.data:
            # Creamos el objeto PermisoPuesto para vincular usuario, puesto y permisos
            permiso = PermisoPuesto(
                usuario=new_user, 
                puesto_id=puesto_id,
                puede_ver=form.puede_ver.data,
                puede_editar=form.puede_editar.data
            )
            db.session.add(permiso)
            
        db.session.commit()
        flash(f'Usuario "{new_user.nombre_completo}" creado con éxito.', 'success')
        return redirect(url_for('admin.list_users'))
    
    # Si la validación falla, volvemos a renderizar la página de lista de usuarios.
    # El formulario 'form' ahora contendrá los errores de validación, que se mostrarán en la plantilla.
    puestos_del_barrio_ids = db.session.scalars(db.select(Puesto.id).where(Puesto.barrio_id == admin_barrio_id)).all()
    user_query = db.select(Usuario).join(Usuario.permisos).where(PermisoPuesto.puesto_id.in_(puestos_del_barrio_ids)).distinct()
    page = request.args.get('page', 1, type=int)
    pagination = db.paginate(user_query.order_by(Usuario.nombre_completo), page=page, per_page=15)
    users = pagination.items

    flash('Hubo errores en el formulario. Por favor, corrígelos.', 'danger')
    return render_template('admin/users.html', 
                           title=f'Usuarios de {current_user.barrio_admin.nombre}', 
                           users=users, 
                           pagination=pagination,
                           create_form=form, # Pasamos el formulario con errores
                           current_barrio=current_user.barrio_admin.nombre)


@admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    admin_barrio_id = current_user.barrio_admin_id
    user_to_edit = db.get_or_404(Usuario, user_id)

    # --- Verificación de Seguridad ---
    # Nos aseguramos que el admin no pueda editar usuarios de otros barrios.
    user_permisos_en_barrio = [p for p in user_to_edit.permisos if p.puesto.barrio_id == admin_barrio_id]
    if not user_permisos_en_barrio and user_to_edit.rol.nombre != 'Administrador':
        abort(403) # No tiene permisos en este barrio, no debería poder editarlo.

    form = EditUserForm(original_user=user_to_edit, barrio_id=admin_barrio_id)

    if form.validate_on_submit():
        # Actualizamos los datos del usuario
        user_to_edit.dni = form.dni.data
        user_to_edit.nombre_completo = form.nombre_completo.data
        user_to_edit.email = form.email.data or None
        if form.password.data:
            user_to_edit.password = form.password.data

        # Actualizamos los permisos: borramos los viejos y creamos los nuevos
        # ¡Solo borramos los permisos de ESTE barrio!
        for permiso in user_permisos_en_barrio:
            db.session.delete(permiso)
        
        for puesto_id in form.puestos.data:
            new_permiso = PermisoPuesto(
                usuario_id=user_to_edit.id,
                puesto_id=puesto_id,
                puede_ver=form.puede_ver.data,
                puede_editar=form.puede_editar.data
            )
            db.session.add(new_permiso)
        
        db.session.commit()
        flash(f'Usuario "{user_to_edit.nombre_completo}" actualizado correctamente.', 'success')
        return redirect(url_for('admin.list_users'))

    elif request.method == 'GET':
        # Poblamos el formulario con los datos actuales del usuario
        form.dni.data = user_to_edit.dni
        form.nombre_completo.data = user_to_edit.nombre_completo
        form.email.data = user_to_edit.email
        # Pre-seleccionamos los puestos y permisos que ya tiene
        form.puestos.data = [p.puesto_id for p in user_permisos_en_barrio]
        if user_permisos_en_barrio:
            # Asumimos que los permisos son consistentes para todos los puestos asignados
            form.puede_ver.data = user_permisos_en_barrio[0].puede_ver
            form.puede_editar.data = user_permisos_en_barrio[0].puede_editar

    return render_template('admin/edit_user.html', title=f"Editar Usuario", form=form, user=user_to_edit)

# --- GESTIÓN DE PUESTOS (Ahora con chequeo de plan) ---

@admin_bp.route('/puestos', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_puestos():
    """Gestiona los puestos DEL BARRIO del admin, si su plan lo permite."""
    
    # --- CHEQUEO DE PLAN ---
    if not current_user.organizacion.plan.puede_crear_puestos:
        flash('Tu plan de suscripción no permite gestionar puestos.', 'danger')
        return redirect(url_for('admin.list_users'))

    admin_barrio_id = current_user.barrio_admin_id
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            # Crea el puesto dentro del barrio del admin
            nuevo_puesto = Puesto(nombre=nombre, barrio_id=admin_barrio_id)
            db.session.add(nuevo_puesto)
            db.session.commit()
            flash(f'Puesto "{nombre}" creado con éxito.', 'success')
        return redirect(url_for('admin.manage_puestos'))
    
    puestos = db.session.scalars(db.select(Puesto).where(Puesto.barrio_id == admin_barrio_id).order_by(Puesto.nombre)).all()
    return render_template('admin/manage_puestos.html', title=f"Gestionar Puestos de {current_user.barrio_admin.nombre}", puestos=puestos)

# (Aquí irían las rutas para editar y borrar puestos, también con el chequeo de plan)




















    




















    