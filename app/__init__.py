# Inicialização do pacote app
from flask import Flask

def create_app():
    app = Flask(__name__, static_folder="static_bot_audio")
    
    # Registrar blueprints
    from .agent.routes import agent_bp
    app.register_blueprint(agent_bp)
    
    # Importar e configurar o webhook principal
    from . import main
    
    return app
