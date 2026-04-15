# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - NOVA VERSÃO
Portal com API REST para front-end React + Nova conversação com FAQ
"""
import re
import os
import base64
import logging
import requests
import urllib.parse
import uuid
import hashlib
from datetime import timedelta, datetime
from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from database_manager import db_manager
from database_adapter import DatabaseAdapter

db_adapter = DatabaseAdapter(db_manager)

from app.bot.bot_handler import BotHandler
from ultramsg_adapter import UltraMsgAdapter
from app.integrations.ultramsg_api import ultramsg_api
from app.bot.swissre_automation import SwissReAutomation
from app.bot.faq_knowledge import FAQ_TOPICS

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__, static_folder='web/client/dist', static_url_path='')
CORS(app, supports_credentials=True)
MAX_QUOTES_PER_DAY = 20
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-12345')

# Configurações UltraMsg
ULTRAMSG_INSTANCE_ID = os.getenv('ULTRAMSG_INSTANCE_ID', 'instance135696')
ULTRAMSG_TOKEN = os.getenv('ULTRAMSG_TOKEN', 'token_padrao')
ULTRAMSG_BASE_URL = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}"

# Configuração MongoDB
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'equinos_seguros')

# Variáveis globais para MongoDB
mongodb_connected = False
mongo_client = None
db = None
conversations_collection = None
clients_collection = None
agents_collection = None
quotations_collection = None
messages_collection = None

# Criar adaptadores
db_adapter = DatabaseAdapter(db_manager)
ultramsg_adapter = UltraMsgAdapter(ultramsg_api)

# Usar adaptadores
bot_handler = BotHandler(
    db_manager=db_adapter,
    ultramsg_api=ultramsg_adapter,
    swissre_automation=SwissReAutomation()
)


# =========================================================================
# FUNÇÕES AUXILIARES
# =========================================================================

@app.get("/reset-client/<phone>")
def reset_client_endpoint(phone):
    db_manager.reset_client(phone)
    return {"status": "ok", "message": f"Cliente {phone} resetado com sucesso."}


def gerar_cotacao_id():
    return f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def count_user_quotes_today(phone):
    today = datetime.now().strftime("%Y-%m-%d")
    if not mongodb_connected:
        return 0
    return db.quotations.count_documents({
        "phone": phone,
        "created_at": {"$regex": f"^{today}"}
    })


def reset_client_session(phone):
    save_client_data_to_db(phone, {}, 'collecting')


# =========================================================================
# MONGODB
# =========================================================================

def init_mongodb():
    global mongodb_connected, mongo_client, db
    global conversations_collection, clients_collection, agents_collection
    global quotations_collection, messages_collection

    if not MONGO_URI:
        logger.warning("MONGO_URI não configurado - MongoDB desabilitado")
        return False

    try:
        import pymongo
        from bson import ObjectId

        logger.info("Tentando conectar ao MongoDB...")

        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')

        db = mongo_client[DB_NAME]
        conversations_collection = db.conversations
        clients_collection = db.clients
        agents_collection = db.agents
        quotations_collection = db.quotations
        messages_collection = db.messages

        mongodb_connected = True
        logger.info("MongoDB conectado com sucesso")

        init_agents_from_env()
        return True

    except ImportError:
        logger.warning("PyMongo não instalado - MongoDB desabilitado")
        return False
    except Exception as e:
        logger.warning(f"Erro ao conectar MongoDB: {str(e)} - Continuando sem MongoDB")
        return False


def parse_agents_from_env():
    agents = []
    agents_env = os.getenv('AGENTS', '')

    if agents_env:
        try:
            for agent_str in agents_env.split(','):
                parts = agent_str.strip().split(':')
                if len(parts) >= 3:
                    email = parts[0].strip()
                    password = parts[1].strip()
                    name = parts[2].strip()
                    role = 'admin' if 'admin' in email.lower() else 'agent'
                    agents.append({
                        'email': email,
                        'name': name,
                        'password': password,
                        'role': role,
                        'active': True
                    })
        except Exception as e:
            logger.error(f"Erro ao parse agentes: {str(e)}")

    if not agents:
        agents = [
            {'email': 'agent1@equinosseguros.com', 'name': 'Agente 1', 'password': 'agent123', 'role': 'agent', 'active': True},
            {'email': 'agent2@equinosseguros.com', 'name': 'Agente 2', 'password': 'agent123', 'role': 'agent', 'active': True},
            {'email': 'admin@equinosseguros.com', 'name': 'Administrador', 'password': 'admin123', 'role': 'admin', 'active': True}
        ]

    return agents


def init_agents_from_env():
    if not mongodb_connected:
        return

    try:
        agents = parse_agents_from_env()
        for agent in agents:
            existing = agents_collection.find_one({'email': agent['email']})
            if not existing:
                agent_data = agent.copy()
                agent_data['password_hash'] = hashlib.md5(agent['password'].encode()).hexdigest()
                del agent_data['password']
                agent_data['created_at'] = datetime.utcnow()
                agents_collection.insert_one(agent_data)
            else:
                new_hash = hashlib.md5(agent['password'].encode()).hexdigest()
                if existing.get('password_hash') != new_hash:
                    agents_collection.update_one(
                        {'email': agent['email']},
                        {'$set': {'password_hash': new_hash, 'updated_at': datetime.utcnow()}}
                    )
    except Exception as e:
        logger.error(f"Erro ao criar agentes: {str(e)}")


# =========================================================================
# ULTRAMSG / WHATSAPP
# =========================================================================

def clean_text_for_whatsapp(text):
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
    try:
        clean_phone = phone.replace('@c.us', '').replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('55') and len(clean_phone) >= 10:
            clean_phone = '55' + clean_phone

        url = f"{ULTRAMSG_BASE_URL}/messages/chat"
        clean_message = clean_text_for_whatsapp(message)

        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,
            'body': clean_message
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        response = requests.post(url, data=data, headers=headers, timeout=15)

        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('sent'):
                return True
        return False

    except Exception as e:
        logger.error(f"Erro ao enviar: {str(e)}")
        return False


def send_ultramsg_document(phone, file_path, caption=""):
    try:
        url = f"{ULTRAMSG_BASE_URL}/messages/document"
        clean_phone = phone.replace('@c.us', '').replace('+', '')

        with open(file_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode("utf-8")

        filename = os.path.basename(file_path)
        data = {
            "token": ULTRAMSG_TOKEN,
            "to": clean_phone,
            "document": encoded_file,
            "filename": filename,
            "caption": clean_text_for_whatsapp(caption),
        }

        payload = urllib.parse.urlencode(data, encoding='utf-8')
        headers = {'content-type': 'application/x-www-form-urlencoded; charset=utf-8'}

        response = requests.post(url, data=payload, headers=headers, timeout=30)
        return response.status_code == 200

    except Exception as e:
        logger.error(f"Erro ao enviar documento: {str(e)}")
        return False


# =========================================================================
# FUNÇÕES DE BANCO
# =========================================================================

def save_message_mongo(phone, sender, message):
    if not mongodb_connected:
        return

    try:
        conversation = conversations_collection.find_one({"phone_number": phone})
        if not conversation:
            conversation_id = conversations_collection.insert_one({
                "phone_number": phone,
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }).inserted_id
        else:
            conversation_id = conversation["_id"]

        message_data = {
            "conversation_id": conversation_id,
            "phone_number": phone,
            "sender": sender,
            "message": message,
            "timestamp": datetime.utcnow()
        }
        db.messages.insert_one(message_data)

    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no MongoDB: {str(e)}")


def save_conversation_to_db(phone, message, response, message_type='bot', agent_email=None, needs_human=False):
    if not mongodb_connected:
        return False
    try:
        conversation = {
            'phone': phone,
            'message': message,
            'response': response,
            'message_type': message_type,
            'agent_email': agent_email,
            'needs_human': needs_human,
            'timestamp': datetime.utcnow(),
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'time': datetime.utcnow().strftime('%H:%M:%S')
        }
        conversations_collection.insert_one(conversation)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {str(e)}")
        return False


def save_client_data_to_db(phone, data, status='collecting'):
    if not mongodb_connected:
        return False
    try:
        client_data = {
            'phone': phone,
            'data': data,
            'status': status,
            'updated_at': datetime.utcnow()
        }
        clients_collection.update_one(
            {'phone': phone},
            {'$set': client_data, '$inc': {'conversation_count': 1}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar cliente: {str(e)}")
        return False


def save_quotation_to_db(phone, client_data, pdf_path=None, status='processing', completed_by='bot', agent_email=None):
    if not mongodb_connected:
        return False
    try:
        quotation = {
            'phone': phone,
            'client_data': client_data,
            'pdf_path': pdf_path,
            'status': status,
            'completed_by': completed_by,
            'agent_email': agent_email,
            'created_at': datetime.utcnow(),
            'completed_at': datetime.utcnow() if status == 'completed' else None
        }
        quotations_collection.insert_one(quotation)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar cotação: {str(e)}")
        return False


def get_client_data_from_db(phone):
    if not mongodb_connected:
        return None
    try:
        return clients_collection.find_one({'phone': phone})
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {str(e)}")
        return None


def authenticate_agent(email, password):
    if not mongodb_connected:
        # Fallback: autenticar via env
        agents = parse_agents_from_env()
        for agent in agents:
            if agent['email'] == email and agent['password'] == password:
                return agent
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


def format_phone_display(phone):
    if not phone:
        return "N/A"
    clean_phone = phone.replace('@c.us', '')
    if clean_phone.startswith('55') and len(clean_phone) >= 12:
        country = clean_phone[:2]
        area = clean_phone[2:4]
        first = clean_phone[4:9]
        second = clean_phone[9:]
        return f"+{country} ({area}) {first}-{second}"
    elif len(clean_phone) >= 10:
        area = clean_phone[:2] if len(clean_phone) == 10 else clean_phone[-10:-8]
        first = clean_phone[-8:-4]
        second = clean_phone[-4:]
        return f"({area}) {first}-{second}"
    else:
        return clean_phone


# =========================================================================
# ROTAS DE API REST (para o front-end React)
# =========================================================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login via API REST"""
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')

    agent = authenticate_agent(email, password)
    if agent:
        session['agent_email'] = agent.get('email', email)
        session['agent_name'] = agent.get('name', email.split('@')[0])
        session['agent_role'] = agent.get('role', 'agent')

        return jsonify({
            "success": True,
            "user": {
                "email": session['agent_email'],
                "name": session['agent_name'],
                "role": session['agent_role'],
                "token": "session-based"
            }
        })
    else:
        return jsonify({"success": False, "error": "Email ou senha incorretos"}), 401


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route('/api/auth/me', methods=['GET'])
def api_me():
    """Retorna dados do agente logado"""
    if 'agent_email' not in session:
        return jsonify({"authenticated": False}), 401

    return jsonify({
        "authenticated": True,
        "user": {
            "email": session['agent_email'],
            "name": session['agent_name'],
            "role": session.get('agent_role', 'agent')
        }
    })


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Estatísticas do dashboard"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    stats = {
        "total_clients": 0,
        "bot_handled": 0,
        "human_handled": 0,
        "human_needed": 0,
        "quotations_completed": 0,
        "quotations_by_bot": 0,
        "quotations_by_human": 0,
        "quotations_failed": 0,
        "today_conversations": 0
    }

    if mongodb_connected:
        try:
            stats = {
                "total_clients": clients_collection.count_documents({}),
                "bot_handled": conversations_collection.count_documents({"message_type": "bot", "needs_human": False}),
                "human_handled": conversations_collection.count_documents({"message_type": "human"}),
                "human_needed": conversations_collection.count_documents({"needs_human": True}),
                "quotations_completed": quotations_collection.count_documents({"status": "completed"}),
                "quotations_by_bot": quotations_collection.count_documents({"completed_by": "bot"}),
                "quotations_by_human": quotations_collection.count_documents({"completed_by": "human"}),
                "quotations_failed": quotations_collection.count_documents({"status": "failed"}),
                "today_conversations": conversations_collection.count_documents({
                    "date": datetime.utcnow().strftime('%Y-%m-%d')
                })
            }
        except Exception as e:
            logger.error(f"Erro ao buscar stats: {str(e)}")

    return jsonify(stats)


@app.route('/api/conversations', methods=['GET'])
def api_conversations():
    """Lista de conversas"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    if not mongodb_connected:
        return jsonify([])

    try:
        pipeline = [
            {"$group": {
                "_id": "$phone_number",
                "last_message": {"$last": "$message"},
                "last_timestamp": {"$last": "$timestamp"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"last_timestamp": -1}}
        ]

        conversations_summary = list(messages_collection.aggregate(pipeline))

        result = []
        for conv in conversations_summary:
            phone = conv.get("_id", "")
            last_ts = conv.get("last_timestamp")
            if last_ts:
                last_ts = (last_ts - timedelta(hours=3)).isoformat()

            result.append({
                "phone": phone,
                "phone_display": format_phone_display(phone),
                "last_message": conv.get("last_message", ""),
                "last_timestamp": last_ts,
                "message_count": conv.get("message_count", 0),
                "needs_human": conv.get("needs_human", False),
                "has_human_response": conv.get("has_human_response", False)
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify([])


@app.route('/api/conversations/<phone>', methods=['GET'])
def api_conversation_detail(phone):
    """Detalhes de uma conversa"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    if not mongodb_connected:
        return jsonify({"messages": [], "client_data": None})

    try:
        messages = list(
            messages_collection.find({"phone_number": phone}).sort("timestamp", 1)
        )

        messages_list = []
        for msg in messages:
            ts = msg.get("timestamp")
            if ts:
                ts = (ts - timedelta(hours=3)).isoformat()

            messages_list.append({
                "sender": msg.get("sender", ""),
                "message": msg.get("message", ""),
                "timestamp": ts
            })

        client_data = clients_collection.find_one({"phone": phone})
        client_info = None
        if client_data and client_data.get('data'):
            client_info = client_data['data']

        return jsonify({
            "phone": phone,
            "phone_display": format_phone_display(phone),
            "messages": messages_list,
            "client_data": client_info
        })

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify({"messages": [], "client_data": None})


@app.route('/api/conversations/<phone>/send', methods=['POST'])
def api_send_message(phone):
    """Enviar mensagem pelo portal"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    try:
        data = request.get_json()
        message = data.get('message', '')

        if not message:
            return jsonify({"error": "Mensagem é obrigatória"}), 400

        success = send_ultramsg_message(phone, message)

        if success:
            save_conversation_to_db(phone, "", message, 'human', session['agent_email'])
            save_message_mongo(phone, "agent", message)

            return jsonify({
                "success": True,
                "message": "Mensagem enviada com sucesso"
            })
        else:
            return jsonify({"success": False, "message": "Erro ao enviar via UltraMsg"}), 500

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversations/<phone>/complete', methods=['POST'])
def api_complete_quotation(phone):
    """Finalizar cotação manualmente"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    try:
        client = get_client_data_from_db(phone)
        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404

        save_quotation_to_db(phone, client.get('data', {}), '', 'completed', 'human', session['agent_email'])

        completion_message = """*Cotação finalizada por nosso especialista!*

Sua proposta personalizada foi processada e será enviada em breve.

Obrigado por escolher a Equinos Seguros! 🐴"""

        send_ultramsg_message(phone, completion_message)
        save_conversation_to_db(phone, "", completion_message, 'human', session['agent_email'])

        return jsonify({"success": True, "message": "Cotação finalizada com sucesso"})

    except Exception as e:
        logger.error(f"Erro ao finalizar cotação: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/quotations', methods=['GET'])
def api_quotations():
    """Lista de cotações"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    if not mongodb_connected:
        return jsonify([])

    try:
        quotations = list(quotations_collection.find().sort("created_at", -1))

        result = []
        for q in quotations:
            created = q.get("created_at")
            if created:
                created = (created - timedelta(hours=3)).isoformat()

            result.append({
                "phone": q.get("phone", ""),
                "phone_display": format_phone_display(q.get("phone", "")),
                "status": q.get("status", ""),
                "completed_by": q.get("completed_by", ""),
                "agent_email": q.get("agent_email", ""),
                "created_at": created,
                "client_data": q.get("client_data", {})
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return jsonify([])


@app.route('/api/faq', methods=['GET'])
def api_faq():
    """Lista de tópicos FAQ"""
    result = []
    for topic_id, topic in FAQ_TOPICS.items():
        result.append({
            "id": topic_id,
            "titulo": topic["titulo"],
            "resumo": topic["resumo"],
            "palavras_chave": topic["palavras_chave"][:5]  # Primeiras 5 para exibição
        })
    return jsonify(result)


# =========================================================================
# ROTAS PRINCIPAIS (Backend)
# =========================================================================

@app.route('/health')
def health_check():
    stats = {}
    if mongodb_connected:
        try:
            stats = {
                "total_clients": clients_collection.count_documents({}),
                "total_conversations": conversations_collection.count_documents({}),
                "quotations_completed": quotations_collection.count_documents({"status": "completed"}),
            }
        except Exception as e:
            stats = {"error": str(e)}

    return jsonify({
        "status": "healthy",
        "timestamp": str(datetime.utcnow()),
        "components": {
            "flask": "ok",
            "ultramsg": "configured" if ULTRAMSG_TOKEN != 'token_padrao' else "not_configured",
            "mongodb": "connected" if mongodb_connected else "disconnected"
        },
        "stats": stats
    }), 200


@app.route('/webhook/ultramsg', methods=['POST'])
def webhook_ultramsg():
    """Webhook principal"""
    try:
        data = request.get_json()

        logger.info(f"Webhook recebido - event_type: {data.get('event_type')}")

        # Ignorar mensagens do próprio bot
        data_field = data.get('data', {})
        from_me = data_field.get('fromMe', False)
        is_self = data_field.get('self', False)

        if from_me or is_self:
            return jsonify({"status": "ignored", "reason": "message_from_bot"}), 200

        event_type = data.get('event_type', '')
        if event_type not in ['message_create', 'message_received', '']:
            return jsonify({"status": "ignored", "reason": f"event_type_{event_type}"}), 200

        phone = data_field.get('from', data.get('from', ''))
        phone = phone.replace('@c.us', '').replace('@g.us', '')

        if not phone:
            return jsonify({"error": "Telefone não encontrado"}), 400

        message = data_field.get('body', data.get('body', ''))
        if not message:
            return jsonify({"status": "ignored", "reason": "empty_message"}), 200

        logger.info(f"Mensagem de {phone}: {message[:100]}...")

        # Salvar mensagem do usuário
        save_message_mongo(phone, "user", message)

        # Processar com bot handler
        result = bot_handler.process_message(phone, message)

        logger.info(f"result: {result}")

        # Salvar resposta do bot
        if isinstance(result, dict) and "response" in result:
            save_message_mongo(phone, "bot", result["response"])

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# =========================================================================
# ROTAS LEGADAS DO PORTAL (mantidas para compatibilidade)
# =========================================================================

@app.route('/agent/login', methods=['GET', 'POST'])
def agent_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        agent = authenticate_agent(email, password)
        if agent:
            session['agent_email'] = agent.get('email', email)
            session['agent_name'] = agent.get('name', email.split('@')[0])
            session['agent_role'] = agent.get('role', 'agent')
            return redirect('/portal')
    return redirect('/portal')


@app.route('/agent/logout')
def agent_logout():
    session.clear()
    return redirect('/portal')


@app.route('/agent/send-message', methods=['POST'])
def agent_send_message():
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    try:
        phone = request.form.get('phone')
        message = request.form.get('message')

        if not phone or not message:
            return jsonify({"error": "Telefone e mensagem são obrigatórios"}), 400

        success = send_ultramsg_message(phone, message)

        if success:
            save_conversation_to_db(phone, "", message, 'human', session['agent_email'])
            return jsonify({"success": True, "message": "Mensagem enviada com sucesso"})
        else:
            return jsonify({"success": False, "message": "Erro ao enviar via UltraMsg"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/agent/complete-quotation', methods=['POST'])
def agent_complete_quotation():
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    try:
        phone = request.form.get('phone')
        client = get_client_data_from_db(phone)
        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404

        save_quotation_to_db(phone, client.get('data', {}), '', 'completed', 'human', session['agent_email'])

        completion_message = "*Cotação finalizada por nosso especialista!*\n\nSua proposta personalizada foi processada e será enviada em breve.\n\nObrigado por escolher a Equinos Seguros!"
        send_ultramsg_message(phone, completion_message)
        save_conversation_to_db(phone, "", completion_message, 'human', session['agent_email'])

        return jsonify({"success": True, "message": "Cotação finalizada com sucesso"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
# SERVIR FRONT-END REACT
# =========================================================================

@app.route('/portal')
@app.route('/portal/')
@app.route('/portal/<path:path>')
def serve_portal(path=''):
    """Serve o front-end React"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'client', 'dist')
    if path and os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, 'index.html')


@app.route('/')
def home():
    agents_info = parse_agents_from_env()
    return jsonify({
        "status": "online",
        "service": "Bot Cotacao Seguros - Nova Versão com FAQ",
        "version": "5.0.0",
        "timestamp": str(datetime.utcnow()),
        "mongodb_connected": mongodb_connected,
        "ultramsg_instance": ULTRAMSG_INSTANCE_ID,
        "agents_configured": len(agents_info),
        "portal_url": "/portal",
        "features": [
            "Bot inteligente com FAQ de 21 temas",
            "Automação SwissRe para cotações",
            "Portal React moderno para agentes",
            "Dashboard completo bot vs humano",
            "API REST para front-end",
            "MongoDB integrado" if mongodb_connected else "MongoDB desabilitado"
        ]
    })


# =========================================================================
# INICIALIZAÇÃO
# =========================================================================

logger.info("Iniciando aplicação...")
init_mongodb()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Iniciando na porta {port}")
    logger.info(f"MongoDB: {'Conectado' if mongodb_connected else 'Desconectado'}")
    logger.info(f"Agentes configurados: {len(parse_agents_from_env())}")
    logger.info(f"Portal disponível em: http://localhost:{port}/portal")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
