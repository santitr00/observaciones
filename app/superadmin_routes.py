from flask import Blueprint, render_template, flash, redirect, url_for, abort
from app import db
from app.forms import CrearOrganizacionForm
from app.models import Organizacion, Plan, Barrio, Rol, Usuario
from flask_login import current_user, login_required
from functools import wraps


# Creamos un Blueprint específico para el Super Admin
superadmin_bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

# Decorador para asegurar que solo el Super Admin acceda a estas rutas
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Asumimos que el Rol 'Super Admin' existe y que el Super Admin no está atado a un barrio
        if not current_user.is_authenticated or current_user.rol.nombre != 'Super Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@superadmin_bp.route('/')
@login_required
@super_admin_required
def index():
    """Página principal del panel de Super Admin."""
    organizaciones = db.session.scalars(db.select(Organizacion).order_by(Organizacion.nombre)).all()
    return render_template('superadmin/dashboard.html', title='Panel de Super Admin', organizaciones=organizaciones)

@superadmin_bp.route('/organizaciones/crear', methods=['GET', 'POST'])
@login_required
@super_admin_required
def crear_organizacion():
    """Ruta para renderizar y procesar el formulario de creación."""
    form = CrearOrganizacionForm()
    if form.validate_on_submit():
        # 1. Crear la nueva organización
        nueva_org = Organizacion(nombre=form.nombre_org.data, plan_id=form.plan.data)
        db.session.add(nueva_org)

        # 2. Obtener el rol de "Admin de Barrio"
        admin_rol = Rol.query.filter_by(nombre='Administrador').first()
        if not admin_rol:
            # Fallback por si no se ha sembrado la BD
            admin_rol = Rol(nombre='Administrador')
            db.session.add(admin_rol)

        # 3. Crear el primer usuario para esa organización
        admin_de_barrio = Usuario(
            dni=form.admin_dni.data,
            nombre_completo=form.admin_nombre.data,
            email=form.admin_email.data,
            rol=admin_rol,
            organizacion=nueva_org,
            barrio_admin_id=form.barrio_a_gestionar.data
        )
        admin_de_barrio.password = form.admin_password.data
        db.session.add(admin_de_barrio)
        
        db.session.commit()
        flash('Nueva organización y su administrador fueron creados con éxito.', 'success')
        return redirect(url_for('superadmin.index'))
    
    return render_template('superadmin/crear_organizacion.html', title='Crear Organización', form=form)