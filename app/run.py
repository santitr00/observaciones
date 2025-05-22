# run.py
from app import create_app
from waitress import serve

app = create_app()

if __name__ == "__main__":
    serve(app, host="192.168.1.64", port=5000, threads=12)
