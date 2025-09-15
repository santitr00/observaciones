import click
from app import db
from app.models import Plan, Rol, Organizacion, Usuario, Barrio, Puesto, PermisoPuesto, Acta
from sqlalchemy.exc import IntegrityError
from flask import current_app
from flask.cli import with_appcontext


def register_commands(app):
    @app.cli.command('seed')
    @click.option('--fresh', is_flag=True, help='Borra todos los datos existentes antes de sembrar.')
    def seed(fresh):
        """Siembra la base de datos con un conjunto completo de datos de prueba."""
        
        if fresh:
            click.echo("Borrando todos los datos existentes...")
            # Borramos en orden inverso para evitar problemas de foreign keys
            db.session.query(PermisoPuesto).delete()
            db.session.query(Puesto).delete()
            db.session.query(Acta).delete() # Si tienes actas
            db.session.query(Usuario).delete()
            db.session.query(Organizacion).delete()
            db.session.query(Barrio).delete()
            db.session.query(Plan).delete()
            db.session.query(Rol).delete()
            db.session.commit()
            click.echo("Datos borrados.")

        try:
            click.echo("Iniciando siembra de datos de prueba...")

            # --- 1. Crear Catálogos (Planes y Roles) ---
            planes = [
                Plan(nombre='Básico', precio=30, puede_crear_puestos=False),
                Plan(nombre='Profesional', precio=50, puede_crear_puestos=False),
                Plan(nombre='Corporativo', precio=100, puede_crear_puestos=True)
            ]
            db.session.add_all(planes)

            roles = [
                Rol(nombre='Super Admin'), 
                Rol(nombre='Administrador'), 
                Rol(nombre='Usuario')
            ]
            db.session.add_all(roles)
            db.session.commit()
            click.echo("Planes y Roles creados.")

            # --- 2. Crear Clientes (Organizaciones) y sus Ubicaciones (Barrios) ---
            # Cliente 1: Un consorcio con plan Corporativo
            org1 = Organizacion(nombre='Consorcio Cadaqués', plan=planes[2])
            barrio1 = Barrio(nombre='Cadaqués')
            puesto1_1 = Puesto(nombre='Portería Principal', barrio=barrio1)
            puesto1_2 = Puesto(nombre='C.O.M.', barrio=barrio1)
            
            # Cliente 2: Una empresa de seguridad con plan Profesional
            org2 = Organizacion(nombre='Seguridad ACME', plan=planes[1])
            barrio2 = Barrio(nombre='Edificio Mitre')
            puesto2_1 = Puesto(nombre='Recepción Mitre', barrio=barrio2)

            # Cliente 3: Un cliente pequeño con plan Básico
            org3 = Organizacion(nombre='Librería El Ateneo', plan=planes[0])
            barrio3 = Barrio(nombre='Sucursal Centro')
            puesto3_1 = Puesto(nombre='Mostrador Principal', barrio=barrio3)

            db.session.add_all([org1, barrio1, puesto1_1, puesto1_2, 
                                org2, barrio2, puesto2_1,
                                org3, barrio3, puesto3_1])
            db.session.commit()
            click.echo("Organizaciones, Barrios y Puestos creados.")

            # --- 3. Crear Usuarios ---
            # Tu cuenta de Super Administrador
            super_admin = Usuario(dni='00000000', nombre_completo='Super Admin', email='tu_email@dominio.com', rol=roles[0], organizacion=org1) # Te asignamos a la primera org por defecto
            super_admin.password = 'password' # Contraseña simple para prueba

            # Un Admin de Barrio para Cadaqués
            admin_cadaques = Usuario(dni='11111111', nombre_completo='Admin Cadaqués', email='admin.cadaques@test.com', rol=roles[1], organizacion=org1, organizacion2=org2, barrio_admin=barrio1)
            admin_cadaques.password = 'password'
            
            # Un guardia para Cadaqués
            guardia_cadaques = Usuario(dni='22222222', nombre_completo='Carlos Guardia', email='c.guardia@test.com', rol=roles[2], organizacion=org1)
            guardia_cadaques.password = 'password'

            # Un guardia para Seguridad ACME
            guardia_acme = Usuario(dni='33333333', nombre_completo='Ana Vigilante', email='a.vigilante@test.com', rol=roles[2], organizacion=org2)
            guardia_acme.password = 'password'

            # Un guardia "Multitarea"
            guardia_multitarea = Usuario(dni='44444444', nombre_completo='Maria Rotativa', email='m.rotativa@test.com', rol=roles[2], organizacion=org1) # Lo asignamos a una org principal
            guardia_multitarea.password = 'password'

            db.session.add_all([super_admin, admin_cadaques, guardia_cadaques, guardia_acme, guardia_multitarea])
            db.session.commit()
            click.echo("Usuarios creados.")

            # --- 4. Asignar Permisos ---
            # El guardia de Cadaqués solo puede ver y editar en la portería principal
            permiso1 = PermisoPuesto(usuario=guardia_cadaques, puesto=puesto1_1, puede_ver=True, puede_editar=True)

            # El guardia de ACME solo puede ver en la recepción
            permiso2 = PermisoPuesto(usuario=guardia_acme, puesto=puesto2_1, puede_ver=True, puede_editar=False)

            # El guardia multitarea tiene permisos en dos lugares diferentes
            permiso3_1 = PermisoPuesto(usuario=guardia_multitarea, puesto=puesto1_2, puede_ver=True, puede_editar=True) # En el C.O.M. de Cadaqués
            permiso3_2 = PermisoPuesto(usuario=guardia_multitarea, puesto=puesto2_1, puede_ver=True, puede_editar=False) # Puede VER la recepción de Mitre, pero no editar

            db.session.add_all([permiso1, permiso2, permiso3_1, permiso3_2])
            db.session.commit()
            click.echo("Permisos asignados.")

            click.echo("¡Siembra de datos de prueba completada con éxito!")

        except IntegrityError:
            db.session.rollback()
            click.echo("Error de integridad. Es posible que los datos ya existan. Prueba a usar la opción --fresh.")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Un error ocurrió durante la siembra: {e}")