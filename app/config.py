# app/config.py
import os

# Calcula la ruta base del proyecto (un nivel arriba de donde está config.py)
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# Define la ruta a la carpeta 'instance' relativa a la base del proyecto
instance_path = os.path.join(basedir, 'instance')
# Define la ruta completa al archivo de la base de datos SQLite dentro de 'instance'
db_path = os.path.join(instance_path, 'observaciones.db')

class Config:
    # ¡MUY IMPORTANTE! Cambia esto por una cadena larga, aleatoria y secreta.
    # Puedes generarla, por ejemplo, en la terminal con: python -c 'import secrets; print(secrets.token_hex(16))'
    # En producción, es mejor usar variables de entorno.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura-y-dificil-de-adivinar'

    # Configuración de la base de datos SQLite
    # Le dice a SQLAlchemy (que usaremos pronto) dónde encontrar nuestra base de datos.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + db_path

    # Opción para desactivar una característica de SQLAlchemy que no usaremos y consume recursos.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Habilita el modo debug de Flask (útil para desarrollo, muestra errores detallados, recarga automáticamente)
    # ¡ASEGÚRATE de que sea False en producción!
    DEBUG = True