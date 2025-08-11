# -*- coding: utf-8 -*-
"""
Rotas do painel de agente
"""

import os
import logging
from flask import Blueprint, render_template_string, request, redirect, url_for, session, jsonify
from app.db.database import Database

logger = logging.getLogger(__name__)

# Criar blueprint
agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

# Inicializar database
database = Database()

# Template de login
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Painel de Agente</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            background: white; 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #333; font-size: 28px; margin-bottom: 5px; }
        .logo p { color: #666; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 500; }
        input { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus { 
            outline: none; 
            border-color: #667eea; 
        }
        button { 
            width: 100%; 
            padding: 14px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .error { 
            color: #e74c3c; 
            margin-top: 15px; 
            text-align: center; 
            padding: 10px;
            background: #fdf2f2;
            border-radius: 6px;
            border: 1px solid #fecaca;
        }
        .footer { text-align: center; margin-top: 20px; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>🔐 Painel de Agente</h1>
            <p>Equinos Seguros - UltraMsg</p>
        </div>
        <form method="POST">
            <div class="form-group">
                <label>Email:</label>
                <input type="email" name="email" required placeholder="seu@email.com">
            </div>
            <div class="form-group">
                <label>Senha:</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            <button type="submit">Entrar</button>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </form>
        <div class="footer">
            Bot de Cotação de Seguros v2.0
        </div>
    </div>
</body>
</html>
"""

# Template de dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Painel de Agente</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #f8fafc;
            color: #333;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 24px; }
        .header .user-info { display: flex; align-items: center; gap: 15px; }
        .logout { color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 6px; }
        .logout:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { 
            background: white; 
            padding: 25px; 
            border-radius: 12px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .stat-card h3 { color: #667eea; font-size: 14px; text-transform: uppercase; margin-bottom: 10px; }
        .stat-card .number { font-size: 32px; font-weight: bold; color: #333; }
        .card { 
            background: white; 
            padding: 25px; 
            border-radius: 12px; 
            margin-bottom: 20px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .card h3 { color: #333; margin-bottom: 20px; font-size: 20px; }
        .status { 
            padding: 8px 12px; 
            border-radius: 20px; 
            font-size: 12px; 
            font-weight: 600;
            text-transform: uppercase;
        }
        .status.success { background: #d4edda; color: #155724; }
        .status.warning { background: #fff3cd; color: #856404; }
        .status.error { background: #f8d7da; color: #721c24; }
        .config-item { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 15px 0; 
            border-bottom: 1px solid #eee;
        }
        .config-item:last-child { border-bottom: none; }
        .config-label { font-weight: 500; }
        .config-value { color: #666; font-family: monospace; }
        .btn { 
            padding: 10px 20px; 
            background: #667eea; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
        }
        .btn:hover { background: #5a6fd8; }
        .refresh-btn { 
            float: right; 
            background: #28a745; 
            margin-bottom: 15px;
        }
        .conversations { max-height: 400px; overflow-y: auto; }
        .conversation-item { 
            padding: 15px; 
            border-bottom: 1px solid #eee; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
        }
        .conversation-item:hover { background: #f8f9fa; }
        .phone { font-weight: 600; color: #333; }
        .time { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dashboard - Agente</h1>
        <div class="user-info">
            <span>{{ agent_email }}</span>
            <a href="/agent/logout" class="logout">Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <h3>Conversas Totais</h3>
                <div class="number">{{ stats.total_conversations }}</div>
            </div>
            <div class="stat-card">
                <h3>Conversas Ativas</h3>
                <div class="number">{{ stats.active_conversations }}</div>
            </div>
            <div class="stat-card">
                <h3>Mensagens Totais</h3>
                <div class="number">{{ stats.total_messages }}</div>
            </div>
            <div class="stat-card">
                <h3>Status Sistema</h3>
                <div class="number">{{ 'Online' if system_status else 'Offline' }}</div>
            </div>
        </div>
        
        <div class="card">
            <h3>🤖 Status do Bot UltraMsg</h3>
            <div class="config-item">
                <span class="config-label">Status da API:</span>
                <span class="status success">✅ Funcionando</span>
            </div>
            <div class="config-item">
                <span class="config-label">Instance ID:</span>
                <span class="config-value">{{ instance_id or 'Não configurado' }}</span>
            </div>
            <div class="config-item">
                <span class="config-label">Webhook URL:</span>
                <span class="config-value">{{ webhook_url }}</span>
            </div>
            <div class="config-item">
                <span class="config-label">Banco de Dados:</span>
                <span class="status {{ 'success' if db_connected else 'error' }}">
                    {{ '✅ Conectado' if db_connected else '❌ Desconectado' }}
                </span>
            </div>
        </div>
        
        <div class="card">
            <h3>💬 Conversas Ativas</h3>
            <button class="btn refresh-btn" onclick="location.reload()">🔄 Atualizar</button>
            <div class="conversations">
                {% if conversations %}
                    {% for conv in conversations %}
                    <div class="conversation-item">
                        <div>
                            <div class="phone">{{ conv.phone_number }}</div>
                            <div class="time">{{ conv.updated_at.strftime('%d/%m/%Y %H:%M') if conv.updated_at else 'N/A' }}</div>
                        </div>
                        <div>
                            <span class="status {{ 'warning' if conv.status == 'awaiting_agent' else 'success' }}">
                                {{ conv.status }}
                            </span>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; color: #666; padding: 40px;">
                        Nenhuma conversa ativa no momento
                    </div>
                {% endif %}
            </div>
        </div>
        
        <div class="card">
            <h3>🔧 Próximos Passos</h3>
            <ul style="line-height: 1.8; color: #666;">
                <li>✅ Configure as variáveis ULTRAMSG_INSTANCE_ID e ULTRAMSG_TOKEN</li>
                <li>✅ Configure o webhook no UltraMsg para: {{ webhook_url }}</li>
                <li>✅ Teste o bot enviando uma mensagem</li>
                <li>📊 Monitore as conversas neste painel</li>
                <li>🔄 Faça handoff quando necessário</li>
            </ul>
        </div>
    </div>
    
    <script>
        // Auto-refresh a cada 30 segundos
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

@agent_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login do agente"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verificação básica (pode ser expandida)
        if _verify_agent_credentials(email, password):
            session['agent_logged_in'] = True
            session['agent_email'] = email
            logger.info(f"Agente logado: {email}")
            return redirect(url_for('agent.dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Email ou senha incorretos")
    
    return render_template_string(LOGIN_TEMPLATE)

@agent_bp.route('/dashboard')
def dashboard():
    """Dashboard principal do agente"""
    if not session.get('agent_logged_in'):
        return redirect(url_for('agent.login'))
    
    try:
        # Obter estatísticas
        stats = database.get_conversation_stats()
        
        # Obter conversas ativas
        conversations = database.get_active_conversations()
        
        # Verificar status do sistema
        instance_id = os.getenv('ULTRAMSG_INSTANCE_ID')
        base_url = os.getenv('BASE_URL', 'http://localhost:8080')
        webhook_url = f"{base_url}/webhook/ultramsg"
        db_connected = database.check_connection()
        
        return render_template_string(DASHBOARD_TEMPLATE,
                                    agent_email=session.get('agent_email'),
                                    stats=stats,
                                    conversations=conversations,
                                    instance_id=instance_id,
                                    webhook_url=webhook_url,
                                    db_connected=db_connected,
                                    system_status=True)
    
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        return f"Erro no dashboard: {str(e)}", 500

@agent_bp.route('/logout')
def logout():
    """Logout do agente"""
    session.clear()
    return redirect(url_for('agent.login'))

@agent_bp.route('/api/conversations')
def api_conversations():
    """API para obter conversas"""
    if not session.get('agent_logged_in'):
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        conversations = database.get_active_conversations()
        
        # Converter para formato JSON
        conversations_data = []
        for conv in conversations:
            conversations_data.append({
                'id': conv.get('_id'),
                'phone_number': conv.get('phone_number'),
                'status': conv.get('status'),
                'created_at': conv.get('created_at').isoformat() if conv.get('created_at') else None,
                'updated_at': conv.get('updated_at').isoformat() if conv.get('updated_at') else None
            })
        
        return jsonify({
            "conversations": conversations_data,
            "total": len(conversations_data)
        })
    
    except Exception as e:
        logger.error(f"Erro na API de conversas: {str(e)}")
        return jsonify({"error": str(e)}), 500

@agent_bp.route('/api/conversation/<conversation_id>/messages')
def api_conversation_messages(conversation_id):
    """API para obter mensagens de uma conversa"""
    if not session.get('agent_logged_in'):
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        messages = database.get_conversation_messages(conversation_id)
        
        # Converter para formato JSON
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.get('_id'),
                'sender': msg.get('sender'),
                'message': msg.get('message'),
                'message_type': msg.get('message_type'),
                'timestamp': msg.get('timestamp').isoformat() if msg.get('timestamp') else None
            })
        
        return jsonify({
            "messages": messages_data,
            "total": len(messages_data)
        })
    
    except Exception as e:
        logger.error(f"Erro na API de mensagens: {str(e)}")
        return jsonify({"error": str(e)}), 500

@agent_bp.route('/api/stats')
def api_stats():
    """API para obter estatísticas"""
    if not session.get('agent_logged_in'):
        return jsonify({"error": "Não autorizado"}), 401
    
    try:
        stats = database.get_conversation_stats()
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Erro na API de estatísticas: {str(e)}")
        return jsonify({"error": str(e)}), 500

def _verify_agent_credentials(email: str, password: str) -> bool:
    """
    Verifica credenciais do agente
    
    Args:
        email: Email do agente
        password: Senha do agente
        
    Returns:
        True se credenciais válidas
    """
    try:
        # Verificação básica para desenvolvimento
        if email == 'admin@equinos.com' and password == 'admin123':
            return True
        
        # Verificação via variáveis de ambiente
        agents = os.getenv('AGENTS', '').split(',')
        
        for agent in agents:
            agent = agent.strip()
            if not agent:
                continue
            
            agent_email = os.getenv(f'AGENT_{agent}_EMAIL')
            agent_password = os.getenv(f'AGENT_{agent}_PASSWORD')  # Ou hash
            
            if agent_email == email and agent_password == password:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro na verificação de credenciais: {str(e)}")
        return False

