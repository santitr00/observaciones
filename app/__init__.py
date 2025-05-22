# app/__init__.py
import os
from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
# Añadir imports
from datetime import timezone, datetime # Importar datetime explícitamente
import pytz
import locale

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.select_barrio' # Redirigir a selección de barrio si no está logueado
login.login_message = "Por favor, inicia sesión y selecciona un barrio para acceder."
login.login_message_category = "info"
csrf = CSRFProtect()
migrate = Migrate()

# Filtro Jinja para convertir UTC a hora local Argentina (para datetime)
def format_datetime_local(dt_value, format="%Y-%m-%d %H:%M"):
    if not dt_value:
        return ""
    # Asegurarse que es un objeto datetime
    if not isinstance(dt_value, datetime):
        return str(dt_value) # Devolver como string si no es datetime

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)

    try:
        local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        dt_local = dt_value.astimezone(local_tz)
        return dt_local.strftime(format)
    except Exception:
        return dt_value.strftime(format) + " UTC (Error TZ)"

# Filtro Jinja para formatear fecha completa en español
def format_date_full_local_es(date_value):
    if not date_value:
        return ""

    # dt_local será el objeto date o datetime a formatear
    dt_local_to_format = date_value

    # Si es un datetime, convertirlo a zona local primero
    if isinstance(date_value, datetime):
        if date_value.tzinfo is None:
            date_value = date_value.replace(tzinfo=timezone.utc)
        try:
            local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            dt_local_to_format = date_value.astimezone(local_tz)
        except Exception as e:
            print(f"Error convirtiendo datetime a local en date_full_local_es: {e}")
            # Usar el datetime original si falla la conversión de zona
            pass # dt_local_to_format ya es date_value

    # Si es solo un date, no necesita conversión de zona horaria
    # dt_local_to_format ya es el objeto date_value

    try:
        original_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
        except locale.Error:
            try:
                 locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
            except locale.Error:
                 print("Advertencia: Locale español no encontrado para formateo de fecha. Usando locale por defecto.")
        
        # Formato: Lunes, 04 de Mayo de 2025
        # Para objetos date, strftime funciona igual que para datetime para estos formatos
        formatted_date = dt_local_to_format.strftime('%A, %d de %B de %Y').capitalize()
        locale.setlocale(locale.LC_TIME, original_locale)
        return formatted_date
    except Exception as e:
        print(f"Error formateando fecha con locale: {e}")
        # Fallback si todo lo demás falla
        if hasattr(dt_local_to_format, 'strftime'):
            return dt_local_to_format.strftime('%Y-%m-%d')
        else:
            return str(dt_local_to_format) + " (Error Locale/Format)"


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
        if 'UPLOAD_FOLDER' in app.config:
                 os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError as e:
         app.logger.error(f"Error creando carpetas: {e}")

    db.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    app.jinja_env.filters['datetime_local'] = format_datetime_local
    app.jinja_env.filters['date_full_local_es'] = format_date_full_local_es
    from app import models
    from . import admin_routes
    app.register_blueprint(admin_routes.bp)
    from . import main_routes
    app.register_blueprint(main_routes.bp)

    return app



    