# -*- coding: utf-8 -*-
"""
WSGI entry point para o Bot de Cotação de Seguros - UltraMsg
Arquivo para deployment no Render, Railway, Heroku, etc.
"""

import os
import sys
from flask import Flask

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

def create_app():
    """
    Factory function para criar a aplicação Flask
    """
    # Criar app Flask
    app = Flask(__name__, static_folder="static_bot_audio")
    
    # Configurar diretórios estáticos
    static_audio_dir = os.path.join(os.path.dirname(__file__), "static_bot_audio")
    static_files_dir = os.path.join(os.path.dirname(__file__), "static_files")
    os.makedirs(static_audio_dir, exist_ok=True)
    os.makedirs(static_files_dir, exist_ok=True)
    
    try:
        # Importar e configurar rotas principais
        from main_ultramsg import configure_routes
        configure_routes(app)
        
        print("✅ Rotas principais configuradas com sucesso")
        
    except ImportError as e:
        print(f"❌ Erro ao importar rotas principais: {e}")
        
        # Configuração de fallback
        @app.route("/")
        def home():
            return {
                "status": "error",
                "message": "Erro na configuração das rotas principais",
                "error": str(e)
            }, 500
    
    try:
        # Registrar blueprint do painel de agente
        from app.agent.routes import agent_bp
        app.register_blueprint(agent_bp)
        print("✅ Painel de agente registrado com sucesso")
        
    except ImportError as e:
        print(f"⚠️ Painel de agente não encontrado: {e}")
        
        # Criar rotas básicas do painel se não existir
        from flask import Blueprint, render_template_string, request, redirect, url_for, session, jsonify
        
        agent_bp = Blueprint('agent', __name__, url_prefix='/agent')
        
        # Template básico de login
        LOGIN_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login - Painel de Agente</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h2 { text-align: center; color: #333; margin-bottom: 30px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; color: #555; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
                button:hover { background: #0056b3; }
                .error { color: red; margin-top: 10px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔐 Painel de Agente</h2>
                <form method="POST">
                    <div class="form-group">
                        <label>Email:</label>
                        <input type="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label>Senha:</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit">Entrar</button>
                    {% if error %}
                    <div class="error">{{ error }}</div>
                    {% endif %}
                </form>
            </div>
        </body>
        </html>
        """
        
        # Template básico de dashboard
        DASHBOARD_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Painel de Agente</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .header h1 { margin: 0; color: #333; }
                .logout { float: right; color: #007bff; text-decoration: none; }
                .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
                .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .status.warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Dashboard - Agente</h1>
                <a href="/agent/logout" class="logout">Sair</a>
            </div>
            
            <div class="card">
                <h3>🤖 Status do Bot UltraMsg</h3>
                <div class="status success">
                    ✅ Bot funcionando com UltraMsg API
                </div>
                <div class="status warning">
                    ⚠️ Painel básico ativo - Configure o módulo completo para mais funcionalidades
                </div>
            </div>
            
            <div class="card">
                <h3>📱 Configuração UltraMsg</h3>
                <p><strong>Instance ID:</strong> {{ instance_id or 'Não configurado' }}</p>
                <p><strong>Webhook URL:</strong> {{ webhook_url or 'Não configurado' }}</p>
                <p><strong>Status:</strong> {{ 'Configurado' if instance_id else 'Pendente' }}</p>
            </div>
            
            <div class="card">
                <h3>🔧 Próximos Passos</h3>
                <ul>
                    <li>Configure as variáveis ULTRAMSG_INSTANCE_ID e ULTRAMSG_TOKEN</li>
                    <li>Configure o webhook no UltraMsg para: {{ webhook_url }}</li>
                    <li>Teste o bot enviando uma mensagem</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        @agent_bp.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                email = request.form.get('email')
                password = request.form.get('password')
                
                # Verificação básica (substitua por verificação real)
                if email == 'admin@equinos.com' and password == 'admin123':
                    session['agent_logged_in'] = True
                    session['agent_email'] = email
                    return redirect(url_for('agent.dashboard'))
                else:
                    return render_template_string(LOGIN_TEMPLATE, error="Email ou senha incorretos")
            
            return render_template_string(LOGIN_TEMPLATE)
        
        @agent_bp.route('/dashboard')
        def dashboard():
            if not session.get('agent_logged_in'):
                return redirect(url_for('agent.login'))
            
            instance_id = os.getenv('ULTRAMSG_INSTANCE_ID')
            base_url = os.getenv('BASE_URL', 'http://localhost:8080')
            webhook_url = f"{base_url}/webhook/ultramsg"
            
            return render_template_string(DASHBOARD_TEMPLATE, 
                                        instance_id=instance_id,
                                        webhook_url=webhook_url)
        
        @agent_bp.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('agent.login'))
        
        @agent_bp.route('/api/conversations')
        def api_conversations():
            if not session.get('agent_logged_in'):
                return jsonify({"error": "Não autorizado"}), 401
            
            # Retornar dados básicos
            return jsonify({
                "conversations": [],
                "total": 0,
                "message": "Configure o módulo completo do painel para ver conversas"
            })
        
        app.register_blueprint(agent_bp)
        print("✅ Painel básico de agente criado")
    
    # Configurar chave secreta
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    return app

# Criar aplicação
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
