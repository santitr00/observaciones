# app/config.py
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar-pero-cambiala'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    REMEMBER_COOKIE_DURATION = timedelta(minutes=30)

    # --- URI para MySQL Local ---
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