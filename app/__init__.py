# app/__init__.py
import os
from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# --- Añadir importación ---
from flask_wtf.csrf import CSRFProtect

# Crear instancias de las extensiones
db = SQLAlchemy()
login = LoginManager()
login.login_view = 'login'
# --- Crear instancia de CSRFProtect ---
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Inicializar las extensiones CON la app creada
    db.init_app(app)
    login.init_app(app)
    # --- Inicializar CSRFProtect ---
    csrf.init_app(app)

    # Asegurarse de que la carpeta de instancia exista
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- Registrar Blueprints o Rutas ---
    with app.app_context():
        from . import routes
        from . import models

        # Crear las tablas de la base de datos si no existen
        # (Considera usar Flask-Migrate para cambios futuros)
        # Comenta esta línea si empiezas a usar Flask-Migrate
        db.create_all()

    # Ruta de prueba opcional
    @app.route('/hello')
    def hello():
        return 'Hola desde la app factory!'

    return app
