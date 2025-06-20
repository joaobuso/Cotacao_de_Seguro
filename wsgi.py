from flask import Flask
from app.main import configure_routes

def create_app():
    app = Flask(__name__, static_folder="app/static_bot_audio")
    configure_routes(app)
    return app

app = create_app()

if __name__ == "__main__":
    app.run()