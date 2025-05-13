# app/config.py
import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# Ya no necesitamos la ruta a instance para la URI de SQLite por defecto
# instance_path = os.path.join(basedir, 'instance')
# db_path = os.path.join(instance_path, 'observaciones.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar-pero-cambiala'

    # --- URI para MySQL Local ---
    # Formato: mysql+pymysql://usuario:contraseña@host/nombre_db
    DB_USER = os.environ.get('DB_USER') or 'adm321'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'aSt6_3237'
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_NAME = os.environ.get('DB_NAME') or 'app_actas'

    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://adm321:aSt6_3237@localhost:3306/app_actas'
    # -----------------------------

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # Límite de 16MB
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'