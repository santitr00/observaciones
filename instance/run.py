# run.py
from app import app # Importa la instancia 'app' desde el paquete 'app' (app/__init__.py)

if __name__ == '__main__':
    # Ejecuta la aplicación usando el servidor de desarrollo de Flask
    # app.run() usará la configuración DEBUG de app.config
    app.run()