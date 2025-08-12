# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - UltraMsg com MongoDB e Painel de Agentes (Corrigido)
"""

import os
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from dotenv import load_dotenv
import pymongo
from bson import ObjectId
import hashlib

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configurações UltraMsg
ULTRAMSG_INSTANCE_ID = os.getenv('ULTRAMSG_INSTANCE_ID')
ULTRAMSG_TOKEN = os.getenv('ULTRAMSG_TOKEN')
ULTRAMSG_BASE_URL = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}"

# Configuração MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'equinos_seguros')

# Variáveis globais para MongoDB
mongo_client = None
db = None
conversations_collection = None
clients_collection = None
agents_collection = None
mongodb_connected = False

# Conectar ao MongoDB
try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    
    # Testar conexão
    mongo_client.admin.command('ping')
    
    # Coleções
    conversations_collection = db.conversations
    clients_collection = db.clients
    agents_collection = db.agents
    
    mongodb_connected = True
    logger.info("✅ Conectado ao MongoDB com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao conectar MongoDB: {str(e)}")
    mongodb_connected = False

# Campos obrigatórios para cotação
REQUIRED_FIELDS = {
    'nome_animal': 'Nome do Animal',
    'valor_animal': 'Valor do Animal (R$)',
    'registro': 'Numero de Registro ou Passaporte',
    'raca': 'Raca',
    'data_nascimento': 'Data de Nascimento',
    'sexo': 'Sexo (inteiro, castrado ou femea)',
    'utilizacao': 'Utilizacao (lazer, salto, laco, etc.)',
    'endereco_cocheira': 'Endereco da Cocheira (CEP e cidade)'
}

# Agentes padrão
DEFAULT_AGENTS = [
    {
        'email': 'AGENT_agent1_EMAIL',
        'name': 'Agente 1',
        'password': 'agent123',
        'role': 'agent',
        'active': True
    },
    {
        'email': 'AGENT_agent2_EMAIL', 
        'name': 'Agente 2',
        'password': 'agent123',
        'role': 'agent',
        'active': True
    },
    {
        'email': 'admin@equinosseguros.com',
        'name': 'Administrador',
        'password': 'admin123',
        'role': 'admin',
        'active': True
    }
]

def init_agents():
    """Inicializar agentes padrão no MongoDB"""
    if not mongodb_connected:
        return
    
    try:
        for agent in DEFAULT_AGENTS:
            existing = agents_collection.find_one({'email': agent['email']})
            if not existing:
                agent_data = agent.copy()
                agent_data['password_hash'] = hashlib.md5(agent['password'].encode()).hexdigest()
                del agent_data['password']
                agent_data['created_at'] = datetime.utcnow()
                agents_collection.insert_one(agent_data)
                logger.info(f"Agente criado: {agent['email']}")
    except Exception as e:
        logger.error(f"Erro ao inicializar agentes: {str(e)}")

def clean_text_for_whatsapp(text):
    """Remove ou substitui caracteres que causam problemas no WhatsApp"""
    replacements = {
        'ç': 'c', 'Ç': 'C', 'ã': 'a', 'Ã': 'A', 'á': 'a', 'Á': 'A',
        'à': 'a', 'À': 'A', 'â': 'a', 'Â': 'A', 'é': 'e', 'É': 'E',
        'ê': 'e', 'Ê': 'E', 'í': 'i', 'Í': 'I', 'ó': 'o', 'Ó': 'O',
        'ô': 'o', 'Ô': 'O', 'õ': 'o', 'Õ': 'O', 'ú': 'u', 'Ú': 'U',
        'ü': 'u', 'Ü': 'U'
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text

def send_ultramsg_message(phone, message):
    """Envia mensagem via UltraMsg com encoding correto"""
    try:
        url = f"{ULTRAMSG_BASE_URL}/messages/chat"
        clean_phone = phone.replace('@c.us', '').replace('+', '')
        clean_message = clean_text_for_whatsapp(message)
        
        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,
            'body': clean_message
        }
        
        payload = urllib.parse.urlencode(data, encoding='utf-8')
        headers = {'content-type': 'application/x-www-form-urlencoded; charset=utf-8'}
        
        logger.info(f"📤 Enviando mensagem para {clean_phone}: {clean_message[:50]}...")
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Mensagem enviada com sucesso")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Erro ao enviar: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {str(e)}")
        return {"success": False, "error": str(e)}

def save_conversation_to_db(phone, message, response, message_type='bot', agent_email=None):
    """Salva conversa no MongoDB"""
    if not mongodb_connected:
        return False
    
    try:
        conversation = {
            'phone': phone,
            'message': message,
            'response': response,
            'message_type': message_type,
            'agent_email': agent_email,
            'timestamp': datetime.utcnow(),
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'time': datetime.utcnow().strftime('%H:%M:%S')
        }
        
        conversations_collection.insert_one(conversation)
        logger.info(f"💾 Conversa salva no MongoDB: {phone}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar conversa: {str(e)}")
        return False

def save_client_data_to_db(phone, data, status='collecting'):
    """Salva dados do cliente no MongoDB"""
    if not mongodb_connected:
        return False
    
    try:
        client_data = {
            'phone': phone,
            'data': data,
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        # Upsert - atualiza se existe, cria se não existe
        result = clients_collection.update_one(
            {'phone': phone},
            {
                '$set': client_data,
                '$inc': {'conversation_count': 1}
            },
            upsert=True
        )
        
        logger.info(f"💾 Dados do cliente salvos: {phone}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cliente: {str(e)}")
        return False

def get_client_data_from_db(phone):
    """Obtém dados do cliente do MongoDB"""
    if not mongodb_connected:
        return None
    
    try:
        client = clients_collection.find_one({'phone': phone})
        return client
    except Exception as e:
        logger.error(f"❌ Erro ao buscar cliente: {str(e)}")
        return None

def extract_animal_data_simple(message, existing_data=None):
    """Extração simples de dados"""
    import re
    
    data = existing_data.copy() if existing_data else {}
    message_lower = message.lower()
    
    patterns = {
        'nome_animal': [r'nome[:\s]+([a-z\s]+)', r'chama[:\s]+([a-z\s]+)', r'cavalo[:\s]+([a-z\s]+)'],
        'valor_animal': [r'valor[:\s]*r?\$?\s*([0-9.,]+)', r'vale[:\s]*r?\$?\s*([0-9.,]+)'],
        'raca': [r'raca[:\s]+([a-z\s]+)', r'quarto\s+de\s+milha', r'mangalarga'],
        'sexo': [r'(inteiro|castrado|femea|macho|egua)'],
        'utilizacao': [r'(lazer|salto|laco|corrida|trabalho|esporte)'],
        'registro': [r'registro[:\s]*([a-z0-9]+)', r'passaporte[:\s]*([a-z0-9]+)'],
        'data_nascimento': [r'nasceu[:\s]*([0-9/]+)', r'([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})']
    }
    
    for field, pattern_list in patterns.items():
        if field not in data or not data[field]:
            for pattern in pattern_list:
                match = re.search(pattern, message_lower)
                if match:
                    value = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                    data[field] = value
                    break
    
    return data

def generate_response_message(phone, message):
    """Gera resposta personalizada"""
    try:
        # Buscar dados existentes do cliente
        client = get_client_data_from_db(phone)
        
        if client is None:
            conversation_count = 1
            existing_data = {}
        else:
            conversation_count = client.get('conversation_count', 0) + 1
            existing_data = client.get('data', {})
        
        # Extrair dados da mensagem atual
        updated_data = extract_animal_data_simple(message, existing_data)
        
        # Verificar campos faltantes
        missing_fields = []
        collected_fields = []
        
        for field_key, field_name in REQUIRED_FIELDS.items():
            if field_key in updated_data and updated_data[field_key]:
                collected_fields.append(f"✅ {field_name}: {updated_data[field_key]}")
            else:
                missing_fields.append(f"❌ {field_name}")
        
        # Determinar status
        status = 'completed' if len(missing_fields) == 0 else 'collecting'
        
        # Salvar dados atualizados
        save_client_data_to_db(phone, updated_data, status)
        
        # Gerar resposta baseada no estado
        if conversation_count == 1:
            response = """🐴 *Ola! Bem-vindo a Equinos Seguros!*

Sou seu assistente virtual e vou te ajudar a fazer a cotacao do seguro do seu equino.

📋 *DADOS NECESSARIOS:*
• Nome do Animal
• Valor do Animal (R$)
• Numero de Registro ou Passaporte
• Raca
• Data de Nascimento
• Sexo (inteiro, castrado ou femea)
• Utilizacao (lazer, salto, laco, etc.)
• Endereco da Cocheira (CEP e cidade)

Pode enviar as informacoes aos poucos. Vou te ajudar! 😊"""
        
        elif len(missing_fields) == 0:
            data_summary = "\\n".join(collected_fields)
            response = f"""✅ *Perfeito! Coletei todas as informacoes:*

{data_summary}

🎉 *Sua cotacao esta sendo processada!*

Em breve voce recebera sua proposta personalizada.
Aguarde alguns instantes... 🔄"""
        
        else:
            collected_list = "\\n".join(collected_fields) if collected_fields else "Nenhum dado coletado ainda."
            missing_list = "\\n".join(missing_fields)
            
            response = f"""📝 *Obrigado pelas informacoes!*

*DADOS JA COLETADOS:*
{collected_list}

*AINDA PRECISO DE:*
{missing_list}

Continue enviando as informacoes que faltam! 😊"""
        
        # Salvar conversa
        save_conversation_to_db(phone, message, response, 'bot')
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return "Ola! Bem-vindo a Equinos Seguros. Vou ajuda-lo com sua cotacao."

def authenticate_agent(email, password):
    """Autentica agente"""
    if not mongodb_connected:
        return None
    
    try:
        password_hash = hashlib.md5(password.encode()).hexdigest()
        agent = agents_collection.find_one({
            'email': email,
            'password_hash': password_hash,
            'active': True
        })
        return agent
    except Exception as e:
        logger.error(f"Erro na autenticação: {str(e)}")
        return None

@app.route('/')
def home():
    """Página inicial"""
    return jsonify({
        "status": "online",
        "service": "Bot de Cotacao de Seguros - MongoDB + Painel de Agentes",
        "version": "3.1.0",
        "mongodb_connected": mongodb_connected,
        "features": [
            "MongoDB integrado",
            "Painel de agentes completo",
            "Historico de conversas",
            "Login por agente",
            "Separacao bot vs humano"
        ],
        "endpoints": {
            "webhook": "/webhook/ultramsg",
            "agent_login": "/agent/login",
            "agent_dashboard": "/agent/dashboard",
            "conversations": "/agent/conversations"
        }
    })

@app.route('/health')
def health_check():
    """Health check"""
    mongodb_status = "connected" if mongodb_connected else "disconnected"
    
    stats = {}
    if mongodb_connected:
        try:
            stats = {
                "total_clients": clients_collection.count_documents({}),
                "total_conversations": conversations_collection.count_documents({}),
                "bot_conversations": conversations_collection.count_documents({"message_type": "bot"}),
                "human_conversations": conversations_collection.count_documents({"message_type": "human"}),
                "active_agents": agents_collection.count_documents({"active": True})
            }
        except Exception as e:
            stats = {"error": f"Could not fetch stats: {str(e)}"}
    
    return jsonify({
        "status": "healthy",
        "timestamp": str(datetime.utcnow()),
        "components": {
            "flask": "ok",
            "ultramsg": "ok" if ULTRAMSG_TOKEN else "not_configured",
            "mongodb": mongodb_status
        },
        "stats": stats
    }), 200

@app.route('/webhook/ultramsg', methods=['POST'])
def webhook_ultramsg():
    """Webhook para UltraMsg"""
    try:
        data = request.get_json()
        
        if not data or data.get('event_type') != 'message_received':
            return jsonify({"status": "ignored"}), 200
        
        message_data = data.get('data', {})
        phone_number = message_data.get('from', '')
        message_body = message_data.get('body', '')
        sender_name = message_data.get('pushname', 'Cliente')
        
        if not phone_number or not message_body or message_data.get('fromMe', False):
            return jsonify({"status": "ignored"}), 200
        
        logger.info(f"📱 Mensagem de {sender_name} ({phone_number}): {message_body}")
        
        # Gerar resposta do bot
        bot_response = generate_response_message(phone_number, message_body)
        
        # Enviar resposta
        result = send_ultramsg_message(phone_number, bot_response)
        
        if result.get('success'):
            return jsonify({
                "status": "success",
                "message_received": message_body,
                "response_sent": bot_response,
                "sender": sender_name,
                "mongodb_connected": mongodb_connected
            }), 200
        else:
            return jsonify({
                "status": "send_failed",
                "error": result.get('error')
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

# PAINEL DE AGENTES

@app.route('/agent/login', methods=['GET', 'POST'])
def agent_login():
    """Login de agentes"""
    if not mongodb_connected:
        return "MongoDB não conectado. Verifique a configuração.", 500
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        agent = authenticate_agent(email, password)
        if agent is not None:
            session['agent_email'] = agent['email']
            session['agent_name'] = agent['name']
            session['agent_role'] = agent['role']
            return redirect(url_for('agent_dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Email ou senha incorretos")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/agent/logout')
def agent_logout():
    """Logout de agentes"""
    session.clear()
    return redirect(url_for('agent_login'))

@app.route('/agent/dashboard')
def agent_dashboard():
    """Dashboard do agente"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Estatísticas
        stats = {
            "total_clients": clients_collection.count_documents({}),
            "total_conversations": conversations_collection.count_documents({}),
            "bot_conversations": conversations_collection.count_documents({"message_type": "bot"}),
            "human_conversations": conversations_collection.count_documents({"message_type": "human"}),
            "today_conversations": conversations_collection.count_documents({
                "date": datetime.utcnow().strftime('%Y-%m-%d')
            })
        }
        
        # Conversas recentes
        recent_conversations = list(conversations_collection.find().sort("timestamp", -1).limit(10))
        
        return render_template_string(DASHBOARD_TEMPLATE, 
                                    agent_name=session['agent_name'],
                                    agent_email=session['agent_email'],
                                    stats=stats,
                                    recent_conversations=recent_conversations)
    
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations')
def agent_conversations():
    """Lista de conversas por cliente"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Buscar clientes únicos
        pipeline = [
            {"$group": {
                "_id": "$phone",
                "last_message": {"$last": "$message"},
                "last_response": {"$last": "$response"},
                "last_timestamp": {"$last": "$timestamp"},
                "message_count": {"$sum": 1},
                "bot_count": {"$sum": {"$cond": [{"$eq": ["$message_type", "bot"]}, 1, 0]}},
                "human_count": {"$sum": {"$cond": [{"$eq": ["$message_type", "human"]}, 1, 0]}}
            }},
            {"$sort": {"last_timestamp": -1}}
        ]
        
        clients_summary = list(conversations_collection.aggregate(pipeline))
        
        return render_template_string(CONVERSATIONS_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    clients=clients_summary)
    
    except Exception as e:
        logger.error(f"Erro nas conversas: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations/<phone>')
def agent_conversation_detail(phone):
    """Detalhes da conversa de um cliente"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Buscar todas as conversas do cliente
        conversations = list(conversations_collection.find({"phone": phone}).sort("timestamp", 1))
        
        # Buscar dados do cliente
        client_data = clients_collection.find_one({"phone": phone})
        
        return render_template_string(CONVERSATION_DETAIL_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    phone=phone,
                                    conversations=conversations,
                                    client_data=client_data)
    
    except Exception as e:
        logger.error(f"Erro nos detalhes: {str(e)}")
        return f"Erro: {str(e)}", 500

# TEMPLATES HTML (mesmos de antes)

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Painel de Agentes</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 50px; }
        .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #555; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .error { color: red; text-align: center; margin-top: 10px; }
        .agents-list { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 20px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🤖 Painel de Agentes</h1>
        <h2>Equinos Seguros</h2>
        
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
        </form>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <div class="agents-list">
            <strong>Agentes de Teste:</strong><br>
            • AGENT_agent1_EMAIL / agent123<br>
            • AGENT_agent2_EMAIL / agent123<br>
            • admin@equinosseguros.com / admin123
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 32px; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; margin-top: 5px; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .conversation { border-bottom: 1px solid #eee; padding: 10px 0; }
        .conversation:last-child { border-bottom: none; }
        .phone { font-weight: bold; color: #007bff; }
        .message { color: #666; margin: 5px 0; }
        .timestamp { font-size: 12px; color: #999; }
        .type-bot { color: #28a745; }
        .type-human { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Dashboard - {{ agent_name }}</h1>
        <div>
            <a href="/agent/conversations" class="btn">💬 Conversas</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_clients }}</div>
                <div class="stat-label">Clientes Totais</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_conversations }}</div>
                <div class="stat-label">Conversas Totais</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.bot_conversations }}</div>
                <div class="stat-label">Atendidas pelo Bot</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.human_conversations }}</div>
                <div class="stat-label">Atendimento Humano</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.today_conversations }}</div>
                <div class="stat-label">Conversas Hoje</div>
            </div>
        </div>
        
        <div class="section">
            <h3>📱 Conversas Recentes</h3>
            {% for conv in recent_conversations %}
            <div class="conversation">
                <div class="phone">{{ conv.phone }}</div>
                <div class="message">{{ conv.message[:100] }}...</div>
                <div class="timestamp">
                    <span class="type-{{ conv.message_type }}">{{ conv.message_type.upper() }}</span>
                    - {{ conv.timestamp.strftime('%d/%m/%Y %H:%M') }}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

CONVERSATIONS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Conversas - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .client-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .client-phone { font-size: 18px; font-weight: bold; color: #007bff; margin-bottom: 10px; }
        .client-stats { display: flex; gap: 20px; margin-bottom: 10px; }
        .stat { font-size: 14px; }
        .stat-bot { color: #28a745; }
        .stat-human { color: #dc3545; }
        .last-message { color: #666; font-style: italic; }
        .timestamp { font-size: 12px; color: #999; margin-top: 5px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; font-size: 14px; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Conversas por Cliente</h1>
        <div>
            <a href="/agent/dashboard" class="btn">📊 Dashboard</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        {% for client in clients %}
        <div class="client-card">
            <div class="client-phone">📱 {{ client._id }}</div>
            <div class="client-stats">
                <div class="stat">Total: {{ client.message_count }} mensagens</div>
                <div class="stat stat-bot">Bot: {{ client.bot_count }}</div>
                <div class="stat stat-human">Humano: {{ client.human_count }}</div>
            </div>
            <div class="last-message">"{{ client.last_message[:100] }}..."</div>
            <div class="timestamp">Última atividade: {{ client.last_timestamp.strftime('%d/%m/%Y %H:%M') }}</div>
            <div style="margin-top: 10px;">
                <a href="/agent/conversations/{{ client._id }}" class="btn">Ver Conversa Completa</a>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

CONVERSATION_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Conversa - {{ phone }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; display: grid; grid-template-columns: 1fr 300px; gap: 20px; }
        .conversation-panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .client-panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .message { margin-bottom: 20px; padding: 15px; border-radius: 8px; }
        .message-user { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .message-bot { background: #f1f8e9; border-left: 4px solid #4caf50; }
        .message-human { background: #fff3e0; border-left: 4px solid #ff9800; }
        .message-header { font-weight: bold; margin-bottom: 5px; }
        .message-content { margin-bottom: 5px; }
        .message-timestamp { font-size: 12px; color: #666; }
        .client-data { margin-bottom: 15px; }
        .field { margin-bottom: 8px; }
        .field-label { font-weight: bold; color: #333; }
        .field-value { color: #666; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Conversa: {{ phone }}</h1>
        <div>
            <a href="/agent/conversations" class="btn">⬅ Voltar</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div class="conversation-panel">
            <h3>Histórico da Conversa</h3>
            {% for conv in conversations %}
            <div class="message message-{{ 'user' if loop.index0 % 2 == 0 else conv.message_type }}">
                <div class="message-header">
                    {% if loop.index0 % 2 == 0 %}
                        👤 Cliente
                    {% elif conv.message_type == 'bot' %}
                        🤖 Bot
                    {% else %}
                        👨‍💼 Agente {{ conv.agent_email or 'Desconhecido' }}
                    {% endif %}
                </div>
                <div class="message-content">
                    {% if loop.index0 % 2 == 0 %}
                        {{ conv.message }}
                    {% else %}
                        {{ conv.response }}
                    {% endif %}
                </div>
                <div class="message-timestamp">{{ conv.timestamp.strftime('%d/%m/%Y %H:%M:%S') }}</div>
            </div>
            {% endfor %}
        </div>
        
        <div class="client-panel">
            <h3>📋 Dados do Cliente</h3>
            {% if client_data and client_data.data %}
            <div class="client-data">
                {% for key, value in client_data.data.items() %}
                <div class="field">
                    <div class="field-label">{{ key.replace('_', ' ').title() }}:</div>
                    <div class="field-value">{{ value }}</div>
                </div>
                {% endfor %}
            </div>
            <div class="field">
                <div class="field-label">Status:</div>
                <div class="field-value">{{ client_data.status }}</div>
            </div>
            <div class="field">
                <div class="field-label">Última atualização:</div>
                <div class="field-value">{{ client_data.updated_at.strftime('%d/%m/%Y %H:%M') }}</div>
            </div>
            {% else %}
            <p>Nenhum dado coletado ainda.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# Inicializar agentes ao iniciar a aplicação
if mongodb_connected:
    init_agents()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Iniciando Bot com MongoDB e Painel de Agentes na porta {port}")
    logger.info(f"📡 UltraMsg API URL: {ULTRAMSG_BASE_URL}")
    logger.info(f"🗄️ MongoDB: {'Conectado' if mongodb_connected else 'Desconectado'}")
    app.run(host='0.0.0.0', port=port, debug=False)