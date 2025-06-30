from app import create_app
from app.agent.routes import agent_bp

app = create_app()

app.register_blueprint(agent_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0")