# app/__init__.py

from flask import Flask, redirect, url_for
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
import click
from datetime import datetime, date
from flask_bootstrap import Bootstrap4
import locale

# 1. Creación de Instancias
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login' # ¡Cambiado a 'login' como punto de entrada!
login_manager.login_message = "Por favor, inicia sesión para continuar."
login_manager.login_message_category = "info"
bootstrap = Bootstrap4()

# 2. Definición del Filtro Personalizado
def format_date_full_local_es(date_value):
    if not isinstance(date_value, (date, datetime)):
        return date_value
    try:
        original_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'es')
    except (locale.Error, NameError):
        original_locale = "C"
    formatted_date = date_value.strftime('%A, %d de %B de %Y').capitalize()
    if original_locale:
        try:
            locale.setlocale(locale.LC_TIME, original_locale)
        except (locale.Error, NameError):
            pass
    return formatted_date

# 3. Application Factory
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bootstrap.init_app(app)

    with app.app_context():
        from . import models
        from .main_routes import main_bp
        app.register_blueprint(main_bp)
        from .admin_routes import admin_bp
        app.register_blueprint(admin_bp)
        from .superadmin_routes import superadmin_bp
        app.register_blueprint(superadmin_bp)
        from . import commands
        commands.register_commands(app)

        # Registro de Filtros
        app.jinja_env.filters['date_full_local_es'] = format_date_full_local_es
        app.jinja_env.filters['datetime_local'] = format_date_full_local_es

        # Ruta Raíz
        @app.route('/')
        def root():
            return redirect(url_for('main.login'))

    return app