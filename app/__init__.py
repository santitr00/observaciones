# app/__init__.py
import os
from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from datetime import timezone
import pytz
import locale

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.select_barrio' # Redirigir a selección de barrio si no está logueado
login.login_message = "Por favor, inicia sesión y selecciona un barrio para acceder."
login.login_message_category = "info"
csrf = CSRFProtect()
migrate = Migrate()

os.makedirs("instance", exist_ok=True)

# Filtros Jinja (definidos antes de create_app)
def format_datetime_local(dt_utc, format="%Y-%m-%d %H:%M"):
    if not dt_utc: return ""
    if dt_utc.tzinfo is None: dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    try:
        local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        dt_local = dt_utc.astimezone(local_tz)
        return dt_local.strftime(format)
    except Exception: return dt_utc.strftime(format) + " UTC (Error TZ)"

def format_date_full_local_es(dt_utc):
    if not dt_utc: return ""
    if dt_utc.tzinfo is None: dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    try:
        local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        dt_local = dt_utc.astimezone(local_tz)
        original_locale = locale.getlocale(locale.LC_TIME)
        try: locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
        except locale.Error:
            try: locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
            except locale.Error: print("Advertencia: Locale español no encontrado.")
        formatted_date = dt_local.strftime('%A, %d de %B de %Y').capitalize()
        locale.setlocale(locale.LC_TIME, original_locale)
        return formatted_date
    except Exception as e:
        print(f"Error formateando fecha local: {e}")
        return dt_utc.strftime('%Y-%m-%d') + " (Error Locale)"

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError as e:
         app.logger.error(f"Error creando carpetas: {e}")

    db.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Registrar filtros Jinja
    app.jinja_env.filters['datetime_local'] = format_datetime_local
    app.jinja_env.filters['date_full_local_es'] = format_date_full_local_es

    # Registrar Blueprints
    from . import admin_routes
    app.register_blueprint(admin_routes.bp)
    from . import main_routes
    app.register_blueprint(main_routes.bp)

    # Ya no se importan modelos aquí directamente

    return app


    