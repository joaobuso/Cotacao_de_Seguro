from flask import Flask

def create_app():
    app = Flask(__name__, static_folder="static_bot_audio")
    
    # Registrar blueprints
    from app.agent.routes import agent_bp
    app.register_blueprint(agent_bp)
    
    # Importar rotas principais
    from app.main import configure_routes
    configure_routes(app)
    
    return app
