# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - Versão Completa com Portal de Resposta
"""
import re
import os
import logging
import requests
import urllib.parse
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from dotenv import load_dotenv
import hashlib
from templates_portal import *
from response_generator import response_generator
from database_manager import db_manager

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)
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

@app.get("/reset-client/<phone>")
def reset_client_endpoint(phone):
    db_manager.reset_client(phone)
    return {"status": "ok", "message": f"Cliente {phone} resetado com sucesso."}

def gerar_cotacao_id():
    return f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

def count_user_quotes_today(phone):
    today = datetime.now().strftime("%Y-%m-%d")
    # Exemplo para MongoDB
    return db.quotations.count_documents({
        "phone": phone,
        "created_at": {"$regex": f"^{today}"}
    })

def reset_client_session(phone):
    save_client_data_to_db(phone, {}, 'collecting')

# Tentar conectar MongoDB
def init_mongodb():
    global mongodb_connected, mongo_client, db, conversations_collection, clients_collection, agents_collection, quotations_collection
    
    if not MONGO_URI:
        logger.warning("⚠️ MONGO_URI não configurado - MongoDB desabilitado")
        return False
    
    try:
        import pymongo
        from bson import ObjectId
        
        logger.info("🔄 Tentando conectar ao MongoDB...")
        
        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        
        db = mongo_client[DB_NAME]
        conversations_collection = db.conversations
        clients_collection = db.clients
        agents_collection = db.agents
        quotations_collection = db.quotations  # Nova coleção para cotações
        
        mongodb_connected = True
        logger.info("✅ MongoDB conectado com sucesso")
        
        # Inicializar agentes via environment variables
        init_agents_from_env()
        
        return True
        
    except ImportError:
        logger.warning("⚠️ PyMongo não instalado - MongoDB desabilitado")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Erro ao conectar MongoDB: {str(e)} - Continuando sem MongoDB")
        return False

def parse_agents_from_env():
    """Parse agentes das environment variables"""
    agents = []
    
    # Formato: AGENTS=agent1@email.com:senha:Nome1,agent2@email.com:senha:Nome2,admin@email.com:senha:Admin
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
                    logger.info(f"👤 Agente configurado: {email}")
        except Exception as e:
            logger.error(f"❌ Erro ao parse agentes: {str(e)}")
    
    # Fallback para agentes padrão se não configurado
    if not agents:
        logger.info("ℹ️ Usando agentes padrão")
        agents = [
            {
                'email': 'agent1@equinosseguros.com',
                'name': 'Agente 1',
                'password': 'agent123',
                'role': 'agent',
                'active': True
            },
            {
                'email': 'agent2@equinosseguros.com', 
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
    
    return agents

def init_agents_from_env():
    """Inicializar agentes das environment variables"""
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
                logger.info(f"👤 Agente criado: {agent['email']}")
            else:
                # Atualizar senha se mudou
                new_hash = hashlib.md5(agent['password'].encode()).hexdigest()
                if existing.get('password_hash') != new_hash:
                    agents_collection.update_one(
                        {'email': agent['email']},
                        {'$set': {'password_hash': new_hash, 'updated_at': datetime.utcnow()}}
                    )
                    logger.info(f"🔄 Senha atualizada: {agent['email']}")
                    
    except Exception as e:
        logger.error(f"❌ Erro ao criar agentes: {str(e)}")

def clean_text_for_whatsapp(text):
    """Remove caracteres especiais"""
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
    """Envia mensagem via UltraMsg - VERSÃO CORRIGIDA"""
    try:
        # Limpar número - remover @c.us e outros caracteres
        clean_phone = phone.replace('@c.us', '').replace('+', '').replace('-', '').replace(' ', '')
        
        # Garantir que tem código do país (55 para Brasil)
        if not clean_phone.startswith('55') and len(clean_phone) >= 10:
            clean_phone = '55' + clean_phone
        
        # URL correta da API UltraMsg
        url = f"{ULTRAMSG_BASE_URL}/messages/chat"
        clean_message = clean_text_for_whatsapp(message)
        
        # Dados no formato correto
        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,  # Apenas números
            'body': clean_message
        }
        
        # Headers corretos
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        logger.info(f"📤 Enviando para {clean_phone}: {clean_message[:50]}...")
        logger.info(f"🔗 URL: {url}")
        logger.info(f"📋 Dados: token={ULTRAMSG_TOKEN[:10]}..., to={clean_phone}, body={clean_message[:30]}...")
        
        # Enviar como form data
        response = requests.post(url, data=data, headers=headers, timeout=15)
        
        logger.info(f"📊 Status: {response.status_code}")
        logger.info(f"📄 Resposta: {response.text[:200]}")
        
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get('sent'):
                logger.info("✅ Mensagem enviada com sucesso")
                return True
            else:
                logger.error(f"❌ UltraMsg erro: {response_json}")
                return False
        else:
            logger.error(f"❌ Erro HTTP: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar: {str(e)}")
        return False

def send_ultramsg_document(phone, document_url, caption=""):
    """Envia documento via UltraMsg"""
    try:
        url = f"{ULTRAMSG_BASE_URL}/messages/document"
        clean_phone = phone.replace('@c.us', '').replace('+', '')
        
        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,
            'document': document_url,
            'caption': clean_text_for_whatsapp(caption)
        }
        
        payload = urllib.parse.urlencode(data, encoding='utf-8')
        headers = {'content-type': 'application/x-www-form-urlencoded; charset=utf-8'}
        
        logger.info(f"📎 Enviando documento para {clean_phone}")
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info("✅ Documento enviado")
            return True
        else:
            logger.error(f"❌ Erro HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar documento: {str(e)}")
        return False

def save_conversation_to_db(phone, message, response, message_type='bot', agent_email=None, needs_human=False):
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
            'needs_human': needs_human,
            'timestamp': datetime.utcnow(),
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'time': datetime.utcnow().strftime('%H:%M:%S')
        }
        
        conversations_collection.insert_one(conversation)
        logger.info(f"💾 Conversa salva: {phone} - Tipo: {message_type}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar conversa: {str(e)}")
        return False

def save_client_data_to_db(phone, data, status='collecting'):
    """Salva dados do cliente"""
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
            {
                '$set': client_data,
                '$inc': {'conversation_count': 1}
            },
            upsert=True
        )
        
        logger.info(f"💾 Cliente salvo: {phone} - Status: {status}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cliente: {str(e)}")
        return False

def save_quotation_to_db(phone, client_data, pdf_path=None, status='processing', completed_by='bot', agent_email=None):
    """Salva cotação no MongoDB"""
    if not mongodb_connected:
        return False
    
    try:
        quotation = {
            'phone': phone,
            'client_data': client_data,
            'pdf_path': pdf_path,
            'status': status,  # processing, completed, failed
            'completed_by': completed_by,  # bot, human
            'agent_email': agent_email,
            'created_at': datetime.utcnow(),
            'completed_at': datetime.utcnow() if status == 'completed' else None
        }
        
        quotations_collection.insert_one(quotation)
        logger.info(f"💾 Cotação salva: {phone} - Status: {status} - Por: {completed_by}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cotação: {str(e)}")
        return False

def get_client_data_from_db(phone):
    """Obtém dados do cliente"""
    if not mongodb_connected:
        return None
    
    try:
        return clients_collection.find_one({'phone': phone})
    except Exception as e:
        logger.error(f"❌ Erro ao buscar cliente: {str(e)}")
        return None

def call_swissre_automation(client_data):
    """Chama a automação SwissRe para gerar cotação"""
    try:
        # Importar módulo SwissRe
        from app.bot.swissre_automation import generate_quotation_pdf
        
        logger.info("🔄 Iniciando automação SwissRe...")
        
        # Chamar função de automação
        result = generate_quotation_pdf(client_data)

        logger.info(f'Resultado Consulta: {result}')
        
        if result and result.get('success'):
            logger.info("✅ Cotação SwissRe gerada com sucesso")
            return {
                'success': True,
                'pdf_url': result.get('pdf_url'),
                'pdf_path': result.get('pdf_path'),
                'message': 'Cotação gerada com sucesso'
            }
        else:
            logger.error("❌ Erro na automação SwissRe")
            return {
                'success': False,
                'message': result.get('message', 'Erro desconhecido na automação')
            }
            
    except ImportError:
        logger.warning("⚠️ Módulo swissre_automation não encontrado")
        return {
            'success': False,
            'message': 'Módulo de automação não disponível'
        }
    except Exception as e:
        logger.error(f"❌ Erro na automação SwissRe: {str(e)}")
        return {
            'success': False,
            'message': f'Erro na automação: {str(e)}'
        }

def extract_animal_data_improved(message, existing_data=None):
    """Extração melhorada de dados com validação"""
    data = existing_data.copy() if existing_data else {}
    message_lower = message.lower()
    message_original = message
    
    # Padrões melhorados para captura
    patterns = {
        'nome_animal': [
            r'nome[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'chama[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'cavalo[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'animal[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)'
        ],
        'valor_animal': [
            r'valor[:\s]*r?\$?\s*([0-9.,]+)',
            r'vale[:\s]*r?\$?\s*([0-9.,]+)',
            r'custa[:\s]*r?\$?\s*([0-9.,]+)',
            r'preco[:\s]*r?\$?\s*([0-9.,]+)',
            r'r\$\s*([0-9.,]+)',
            r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',
            r'([0-9]+\.?[0-9]*\.?[0-9]*)'
        ],
        'raca': [
            r'raca[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'quarto\s+de\s+milha',
            r'mangalarga',
            r'puro\s+sangue',
            r'crioulo',
            r'campolina',
            r'brasileiro\s+de\s+hipismo'
        ],
        'sexo': [
            r'(inteiro|castrado|femea|macho|egua|garanhao)',
            r'sexo[:\s]*(inteiro|castrado|femea|macho|egua|garanhao)'
        ],
        'utilizacao': [
            r'utilizacao[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'uso[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'(lazer|salto|laco|corrida|trabalho|esporte|hipismo|adestramento|vaquejada|tambor|baliza)'
        ],
        'registro': [
            r'registro[:\s]*([a-z0-9\-]+)',
            r'numero[:\s]*([a-z0-9\-]+)',
            r'([0-9]{4,8})'
        ],
        'data_nascimento': [
            r'nasceu[:\s]*([0-9/\-]+)',
            r'nascimento[:\s]*([0-9/\-]+)',
            r'data[:\s]*([0-9/\-]+)',
            r'([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{4})',
            r'([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2})'
        ],
        'endereco': [
            r'endereco[:\s]*([^,\n]+)',
            r'cocheira[:\s]*([^,\n]+)',
            r'cep[:\s]*([0-9\-\s]+)',
            r'cidade[:\s]*([a-záêçõã\s]+)',
            r'([0-9]{5}[\-\s]?[0-9]{3})',
            r'([a-záêçõã\s]+\s+[a-z]{2})'
        ]
    }
    
    # Extrair dados usando padrões
    for field, pattern_list in patterns.items():
        if field not in data or not data[field]:
            for pattern in pattern_list:
                match = re.search(pattern, message_lower)
                if match:
                    value = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                    
                    # Limpeza e validação específica por campo
                    if field == 'valor_animal':
                        value = re.sub(r'[^\d.,]', '', value)
                        if value and len(value) >= 3:
                            data[field] = value
                    elif field == 'nome_animal':
                        if len(value) >= 2 and not value.isdigit() and not re.match(r'^[0-9.,]+$', value):
                            data[field] = value.title()
                    elif field == 'data_nascimento':
                        if re.match(r'[0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4}', value):
                            data[field] = value
                    elif field == 'endereco':
                        if len(value) >= 5:
                            data[field] = value
                    else:
                        data[field] = value
                    
                    break
    
    return data

def check_all_required_fields(data: dict) -> bool:
    required = [
        "nome",
        "cpf",
        "nome_animal",
        "valor_animal",
        "raca",
        "data_nascimento",
        "sexo",
        "utilizacao",
        "rua",
        "numero",
        "bairro",
        "cidade",
        "estado",
        "cep"
    ]
    return all(str(data.get(f, "")).strip() for f in required)

def check_human_request(message):
    """Verifica se cliente quer falar com humano"""
    human_keywords = [
        'falar com atendente', 'atendente humano', 'pessoa real',
        'nao entendi', 'nao consigo', 'ajuda humana',
        'transferir', 'operador', 'suporte humano',
        'complicado', 'dificil', 'nao sei'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in human_keywords)

def generate_bot_response(phone, message):
    try:
        # 🧮 Limite diário
        if count_user_quotes_today(phone) >= MAX_QUOTES_PER_DAY:
            return "⚠️ Você atingiu o limite de 20 cotações por hoje. Tente novamente amanhã ou fale com nosso atendimento."

        # 📊 Buscar dados existentes
        client = get_client_data_from_db(phone)
        conversation_count = client.get('conversation_count', 0) + 1 if client else 0
        existing_data = client.get('data', {}) if client else {}

        # 🧠 Extrair dados da mensagem
        updated_data = response_generator.extract_animal_data(message, existing_data)

        # 🆕 Se for nova cotação (ex: usuário digitou 'nova cotação')
        if message.strip().lower() in ["nova cotacao", "nova cotação", "nova"]:
            reset_client_session(phone)
            updated_data = {}
            updated_data["cotacao_id"] = gerar_cotacao_id()
            status = 'collecting'
        else:
            status = 'completed' if check_all_required_fields(updated_data) else 'collecting'

        # 💾 Salvar dados
        save_client_data_to_db(phone, updated_data, status)

        # 📝 Gerar resposta
        bot_response = response_generator.generate_response(phone, message, {'data': updated_data}, conversation_count)

        # 🐎 Se todos os dados obrigatórios estiverem preenchidos — chama automação SwissRe
        if status == 'completed':
            logger.info(f"🎯 Dados completos para {phone}, iniciando SwissRe")
            swissre_result = call_swissre_automation(updated_data)

            if swissre_result.get('success'):
                save_quotation_to_db(phone, updated_data, swissre_result.get('pdf_path'), 'completed', 'bot')
                if swissre_result.get('pdf_path'):
                    send_ultramsg_document(phone, swissre_result['pdf_path'], "🎉 Sua cotação de seguro equino está pronta!")

                resumo = response_generator.format_final_summary({'data': updated_data})
                bot_response = f"{resumo}\n\n✅ Proposta enviada via WhatsApp."

            else:
                save_quotation_to_db(phone, updated_data, None, 'failed', 'bot')
                bot_response = f"⚠️ Houve um erro ao gerar a cotação: {swissre_result.get('message', 'erro desconhecido')}."
        # else:
        #     save_quotation_to_db(phone, updated_data, None, 'failed', 'bot')
        #     bot_response = f"⚠️ Houve um erro na etapa de cotação, mas não se preocupe. Um atendente entrará em contato com você!"
        # 💾 Salvar conversa
        save_conversation_to_db(phone, message, bot_response, 'bot')
        return bot_response

    except Exception as e:
        logger.error(f"❌ Erro ao gerar resposta: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."

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
        logger.error(f"❌ Erro na autenticação: {str(e)}")
        return None

# ROTAS PRINCIPAIS

@app.route('/')
def home():
    """Página inicial"""
    agents_info = parse_agents_from_env()
    return jsonify({
        "status": "online",
        "service": "Bot Cotacao Seguros - Portal Completo",
        "version": "4.0.0",
        "timestamp": str(datetime.utcnow()),
        "mongodb_connected": mongodb_connected,
        "ultramsg_instance": ULTRAMSG_INSTANCE_ID,
        "agents_configured": len(agents_info),
        "features": [
            "Bot inteligente com automacao SwissRe",
            "Portal de resposta para agentes",
            "Dashboard completo bot vs humano",
            "Cotacoes finalizadas automaticamente",
            "Envio de PDF via WhatsApp",
            "MongoDB integrado" if mongodb_connected else "MongoDB desabilitado"
        ]
    })

@app.route('/health')
def health_check():
    """Health check"""
    stats = {}
    if mongodb_connected:
        try:
            stats = {
                "total_clients": clients_collection.count_documents({}),
                "total_conversations": conversations_collection.count_documents({}),
                "bot_conversations": conversations_collection.count_documents({"message_type": "bot", "needs_human": False}),
                "human_conversations": conversations_collection.count_documents({"message_type": "human"}),
                "human_needed": conversations_collection.count_documents({"needs_human": True}),
                "quotations_completed": quotations_collection.count_documents({"status": "completed"}),
                "quotations_by_bot": quotations_collection.count_documents({"completed_by": "bot"}),
                "quotations_by_human": quotations_collection.count_documents({"completed_by": "human"}),
                "active_agents": agents_collection.count_documents({"active": True})
            }
        except Exception as e:
            stats = {"error": f"Erro ao buscar stats: {str(e)}"}
    
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
        
        if not data or data.get('event_type') != 'message_received':
            return jsonify({"status": "ignored"}), 200
        
        message_data = data.get('data', {})
        phone_number = message_data.get('from', '')
        message_body = message_data.get('body', '')
        sender_name = message_data.get('pushname', 'Cliente')
        
        if not phone_number or not message_body or message_data.get('fromMe', False):
            return jsonify({"status": "ignored"}), 200
        
        logger.info(f"📱 Mensagem de {sender_name} ({phone_number}): {message_body}")
        
        # Gerar resposta
        bot_response = generate_bot_response(phone_number, message_body)
        
        # Enviar resposta
        success = send_ultramsg_message(phone_number, bot_response)
        
        if success:
            return jsonify({
                "status": "success",
                "message_received": message_body,
                "response_sent": bot_response[:100] + "...",
                "sender": sender_name,
                "mongodb_connected": mongodb_connected
            }), 200
        else:
            return jsonify({
                "status": "send_failed",
                "message_received": message_body
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/test')
def webhook_test():
    """Teste do webhook"""
    test_response = generate_bot_response("test_phone", "oi")
    return jsonify({
        "status": "test_success",
        "bot_response": test_response,
        "mongodb_connected": mongodb_connected,
        "ultramsg_configured": ULTRAMSG_TOKEN != 'token_padrao',
        "agents_configured": len(parse_agents_from_env())
    })

# PAINEL DE AGENTES COM PORTAL DE RESPOSTA

@app.route('/agent/login', methods=['GET', 'POST'])
def agent_login():
    """Login de agentes"""
    if not mongodb_connected:
        return jsonify({
            "error": "MongoDB não conectado",
            "message": "Configure MONGO_URI para usar o painel de agentes"
        }), 500
    
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
            agents_list = [f"• {a['email']} / {a['password']}" for a in parse_agents_from_env()]
            return render_template_string(LOGIN_TEMPLATE, 
                                        error="Email ou senha incorretos",
                                        agents_list="\\n".join(agents_list))
    
    agents_list = [f"• {a['email']} / {a['password']}" for a in parse_agents_from_env()]
    return render_template_string(LOGIN_TEMPLATE, agents_list="\\n".join(agents_list))

@app.route('/agent/logout')
def agent_logout():
    """Logout"""
    session.clear()
    return redirect(url_for('agent_login'))

@app.route('/agent/dashboard')
def agent_dashboard():
    """Dashboard completo"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Estatísticas completas
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
        
        # Conversas que precisam de atendimento humano
        human_needed = list(conversations_collection.find({"needs_human": True}).sort("timestamp", -1).limit(5))
        
        # Cotações recentes
        recent_quotations = list(quotations_collection.find().sort("created_at", -1).limit(5))
        
        return render_template_string(DASHBOARD_COMPLETE_TEMPLATE, 
                                    agent_name=session['agent_name'],
                                    stats=stats,
                                    human_needed=human_needed,
                                    recent_quotations=recent_quotations)
    
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations')
def agent_conversations():
    """Lista conversas com números formatados"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        pipeline = [
            {"$group": {
                "_id": "$phone",
                "last_message": {"$last": "$message"},
                "last_response": {"$last": "$response"},
                "last_timestamp": {"$last": "$timestamp"},
                "message_count": {"$sum": 1},
                "needs_human": {"$max": "$needs_human"},
                "has_human_response": {"$max": {"$cond": [{"$eq": ["$message_type", "human"]}, 1, 0]}}
            }},
            {"$sort": {"last_timestamp": -1}}
        ]
        
        conversations_summary = list(conversations_collection.aggregate(pipeline))
        
        return render_template_string(CONVERSATIONS_LIST_TEMPLATE_FIXED,
                                    agent_name=session['agent_name'],
                                    conversations=conversations_summary,
                                    format_phone_display=format_phone_display)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations/<phone>')
def agent_conversation_detail(phone):
    """Detalhes com número formatado"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        conversations = list(conversations_collection.find({"phone": phone}).sort("timestamp", 1))
        client_data = clients_collection.find_one({"phone": phone})
        
        return render_template_string(CONVERSATION_PORTAL_TEMPLATE_FIXED,
                                    agent_name=session['agent_name'],
                                    agent_email=session['agent_email'],
                                    phone=phone,
                                    conversations=conversations,
                                    client_data=client_data,
                                    format_phone_display=format_phone_display)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

def format_phone_display(phone):
    """Formata número para exibição amigável"""
    # Remover @c.us
    clean_phone = phone.replace('@c.us', '')
    
    # Se tem código do país brasileiro (55)
    if clean_phone.startswith('55') and len(clean_phone) >= 12:
        # Formato: +55 (19) 98811-8043
        country = clean_phone[:2]
        area = clean_phone[2:4]
        first = clean_phone[4:9]
        second = clean_phone[9:]
        return f"+{country} ({area}) {first}-{second}"
    elif len(clean_phone) >= 10:
        # Formato: (19) 98811-8043
        area = clean_phone[:2] if len(clean_phone) == 10 else clean_phone[-10:-8]
        first = clean_phone[-8:-4]
        second = clean_phone[-4:]
        return f"({area}) {first}-{second}"
    else:
        return clean_phone

# FUNÇÃO PARA OBTER NÚMERO LIMPO PARA PROCESSAMENTO
def get_clean_phone(phone):
    """Obtém número limpo para processamento interno"""
    return phone.replace('@c.us', '').replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')

@app.route('/agent/send-message', methods=['POST'])
def agent_send_message():
    """Enviar mensagem pelo portal - VERSÃO CORRIGIDA"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        phone = request.form.get('phone')
        message = request.form.get('message')
        
        if not phone or not message:
            return jsonify({"error": "Telefone e mensagem são obrigatórios"}), 400
        
        logger.info(f"🔄 Agente {session['agent_email']} enviando mensagem para {phone}")
        
        # Enviar mensagem via UltraMsg
        success = send_ultramsg_message(phone, message)
        
        if success:
            # Salvar no banco como resposta humana
            save_conversation_to_db(phone, "", message, 'human', session['agent_email'])
            
            logger.info(f"✅ Mensagem enviada e salva para {phone}")
            
            return jsonify({
                "success": True,
                "message": "Mensagem enviada com sucesso",
                "phone_display": format_phone_display(phone)
            })
        else:
            logger.error(f"❌ Falha ao enviar mensagem para {phone}")
            return jsonify({
                "success": False,
                "message": "Erro ao enviar mensagem via UltraMsg"
            }), 500
    
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/agent/complete-quotation', methods=['POST'])
def agent_complete_quotation():
    """Finalizar cotação manualmente"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        phone = request.form.get('phone')
        pdf_path = request.form.get('pdf_path', '')
        
        if not phone:
            return jsonify({"error": "Telefone é obrigatório"}), 400
        
        # Buscar dados do cliente
        client = get_client_data_from_db(phone)
        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404
        
        # Salvar cotação como completa pelo humano
        save_quotation_to_db(phone, client.get('data', {}), pdf_path, 'completed', 'human', session['agent_email'])
        
        # Enviar mensagem de finalização
        completion_message = """🎉 *Cotacao finalizada por nosso especialista!*

Sua proposta personalizada foi processada e
sera enviada em breve.

Obrigado por escolher a Equinos Seguros! 🐴✨"""
        
        send_ultramsg_message(phone, completion_message)
        save_conversation_to_db(phone, "", completion_message, 'human', session['agent_email'])
        
        # Enviar PDF se fornecido
        if pdf_path:
            send_ultramsg_document(phone, pdf_path, "📋 Sua cotacao personalizada")
        
        return jsonify({
            "success": True,
            "message": "Cotação finalizada com sucesso"
        })
    
    except Exception as e:
        logger.error(f"❌ Erro ao finalizar cotação: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/agent/quotations')
def agent_quotations():
    """Lista de cotações"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        quotations = list(quotations_collection.find().sort("created_at", -1))
        
        return render_template_string(QUOTATIONS_LIST_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    quotations=quotations)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

# TEMPLATES HTML (continuação no próximo arquivo devido ao limite de tamanho)

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Portal Completo</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 50px; }
        .container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .error { color: red; text-align: center; margin-top: 10px; }
        .info { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 20px; font-size: 12px; white-space: pre-line; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Portal Completo</h1>
        <h3>Bot + Humano + Cotações</h3>
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
        
        <div class="info">
            <strong>Agentes Configurados:</strong>
            {{ agents_list }}
        </div>
    </div>
</body>
</html>
"""
# TEMPLATE CORRIGIDO PARA LISTA DE CONVERSAS
CONVERSATIONS_LIST_TEMPLATE_FIXED = """
<!DOCTYPE html>
<html>
<head>
    <title>Conversas - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .conversation-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .conversation-phone { font-size: 18px; font-weight: bold; color: #007bff; margin-bottom: 10px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; color: white; margin-left: 10px; }
        .badge-danger { background: #dc3545; }
        .badge-success { background: #28a745; }
        .badge-info { background: #17a2b8; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Todas as Conversas</h1>
        <div>
            <a href="/agent/dashboard" class="btn">⬅ Dashboard</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        {% for conv in conversations %}
        <div class="conversation-card">
            <div class="conversation-phone">
                📱 {{ format_phone_display(conv._id) }}
                {% if conv.needs_human %}
                    <span class="badge badge-danger">PRECISA HUMANO</span>
                {% endif %}
                {% if conv.has_human_response %}
                    <span class="badge badge-success">COM RESPOSTA HUMANA</span>
                {% else %}
                    <span class="badge badge-info">APENAS BOT</span>
                {% endif %}
            </div>
            <div style="margin-bottom: 15px; color: #666;">
                <strong>Última mensagem:</strong> "{{ conv.last_message[:150] }}..."<br>
                <strong>Última atividade:</strong> {{ conv.last_timestamp.strftime('%d/%m/%Y %H:%M') }}
            </div>
            <div>
                <a href="/agent/conversations/{{ conv._id }}" class="btn">👀 Ver Conversa</a>
                {% if conv.needs_human %}
                    <a href="/agent/conversations/{{ conv._id }}" class="btn" style="background: #dc3545;">🚨 Responder</a>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

# TEMPLATE CORRIGIDO PARA PORTAL DE RESPOSTA
CONVERSATION_PORTAL_TEMPLATE_FIXED = """
<!DOCTYPE html>
<html>
<head>
    <title>Portal - {{ format_phone_display(phone) }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; display: grid; grid-template-columns: 1fr 350px; gap: 20px; }
        .conversation-panel { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; flex-direction: column; height: 600px; }
        .conversation-messages { flex: 1; padding: 20px; overflow-y: auto; }
        .conversation-input { padding: 20px; border-top: 1px solid #eee; }
        .message { margin-bottom: 15px; padding: 15px; border-radius: 8px; }
        .message-user { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .message-bot { background: #f1f8e9; border-left: 4px solid #4caf50; }
        .message-human { background: #fff3e0; border-left: 4px solid #ff9800; }
        .btn { padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; }
        .btn-success { background: #28a745; }
        .btn-danger { background: #dc3545; }
        .form-control { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .textarea { min-height: 80px; resize: vertical; }
        .alert { padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-danger { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Portal: {{ format_phone_display(phone) }}</h1>
        <div>
            <a href="/agent/conversations" class="btn">⬅ Voltar</a>
        </div>
    </div>
    
    <div class="container">
        <div class="conversation-panel">
            <div style="padding: 20px; border-bottom: 1px solid #eee;">
                <h3>📱 Conversa com {{ format_phone_display(phone) }}</h3>
                <div id="alerts"></div>
            </div>
            
            <div class="conversation-messages" id="messages">
                {% for conv in conversations %}
                <div class="message {% if conv.message_type == 'human' %}message-human{% elif conv.message_type == 'bot' %}message-bot{% else %}message-user{% endif %}">
                    <div style="font-weight: bold; margin-bottom: 8px;">
                        {% if conv.message_type == 'human' %}
                            👨‍💼 {{ conv.agent_email or 'Agente' }}
                        {% elif conv.message_type == 'bot' %}
                            🤖 Bot
                        {% else %}
                            👤 Cliente
                        {% endif %}
                        <span style="font-size: 12px; color: #666; margin-left: 10px;">{{ conv.timestamp.strftime('%d/%m %H:%M') }}</span>
                    </div>
                    <div style="line-height: 1.4;">
                        {% if conv.message_type == 'human' or conv.message_type == 'bot' %}
                            {{ (conv.response or conv.message) | replace('\n', '<br>') | safe }}
                        {% else %}
                            {{ conv.message | replace('\n', '<br>') | safe }}
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div class="conversation-input">
                <form id="messageForm">
                    <div style="margin-bottom: 10px;">
                        <textarea name="message" class="form-control textarea" placeholder="Digite sua resposta..." required></textarea>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button type="submit" class="btn btn-success">📤 Enviar</button>
                        <button type="button" class="btn btn-danger" onclick="completeQuotation()">✅ Finalizar</button>
                    </div>
                </form>
            </div>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3>📋 Dados do Cliente</h3>
            {% if client_data and client_data.data %}
            {% for key, value in client_data.data.items() %}
            <div style="margin-bottom: 10px;">
                <strong>{{ key.replace('_', ' ').title() }}:</strong><br>
                <span style="color: #666;">{{ value }}</span>
            </div>
            {% endfor %}
            {% else %}
            <p>Nenhum dado coletado ainda.</p>
            {% endif %}
            
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                <h4>⚡ Mensagens Rápidas</h4>
                <button class="btn" style="margin: 2px; font-size: 12px;" onclick="sendQuick('Ola! Sou especialista da Equinos Seguros.')">👋 Saudação</button><br>
                <button class="btn" style="margin: 2px; font-size: 12px;" onclick="sendQuick('Preciso de mais informacoes para sua cotacao.')">📋 Solicitar</button><br>
                <button class="btn" style="margin: 2px; font-size: 12px;" onclick="sendQuick('Sua cotacao esta sendo processada!')">⏳ Processando</button>
            </div>
        </div>
    </div>

    <script>
        const phone = '{{ phone }}';
        
        document.getElementById('messageForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('phone', phone);
            formData.append('message', this.message.value);
            
            showAlert('Enviando mensagem...', 'info');
            
            fetch('/agent/send-message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('✅ Mensagem enviada!', 'success');
                    this.message.value = '';
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showAlert('❌ Erro: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                showAlert('❌ Erro de conexão: ' + error, 'danger');
            });
        });
        
        function sendQuick(message) {
            const formData = new FormData();
            formData.append('phone', phone);
            formData.append('message', message);
            
            showAlert('Enviando...', 'info');
            
            fetch('/agent/send-message', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('✅ Enviado!', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showAlert('❌ Erro: ' + data.message, 'danger');
                }
            });
        }
        
        function completeQuotation() {
            if (confirm('Finalizar cotação para este cliente?')) {
                const formData = new FormData();
                formData.append('phone', phone);
                
                fetch('/agent/complete-quotation', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('✅ Cotação finalizada!', 'success');
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        showAlert('❌ Erro: ' + data.message, 'danger');
                    }
                });
            }
        }
        
        function showAlert(message, type) {
            const alertsDiv = document.getElementById('alerts');
            const alertClass = type === 'success' ? 'alert-success' : type === 'danger' ? 'alert-danger' : 'alert-info';
            alertsDiv.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
            setTimeout(() => alertsDiv.innerHTML = '', 4000);
        }
        
        // Auto-scroll
        const messagesDiv = document.getElementById('messages');
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    </script>
</body>
</html>
"""
# Inicializar MongoDB ao iniciar
logger.info("🚀 Iniciando aplicação portal completo...")
init_mongodb()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando na porta {port}")
    logger.info(f"🗄️ MongoDB: {'Conectado' if mongodb_connected else 'Desconectado'}")
    logger.info(f"👥 Agentes configurados: {len(parse_agents_from_env())}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)