# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - Versão Completa com Portal de Resposta
"""

import os
import logging
import requests
import urllib.parse
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from dotenv import load_dotenv
import hashlib
from templates_portal import *

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)
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
    """Envia mensagem via UltraMsg"""
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
        
        logger.info(f"📤 Enviando para {clean_phone}: {clean_message[:50]}...")
        
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Mensagem enviada")
            return True
        else:
            logger.error(f"❌ Erro HTTP: {response.status_code}")
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

def save_quotation_to_db(phone, client_data, pdf_url=None, status='processing', completed_by='bot', agent_email=None):
    """Salva cotação no MongoDB"""
    if not mongodb_connected:
        return False
    
    try:
        quotation = {
            'phone': phone,
            'client_data': client_data,
            'pdf_url': pdf_url,
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
            r'passaporte[:\s]*([a-z0-9\-]+)',
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
        'endereco_cocheira': [
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
                    elif field == 'endereco_cocheira':
                        if len(value) >= 5:
                            data[field] = value
                    else:
                        data[field] = value
                    
                    break
    
    return data

def check_all_required_fields(data):
    """Verifica se todos os campos obrigatórios estão preenchidos"""
    required_fields = [
        'nome_animal', 'valor_animal', 'registro', 'raca',
        'data_nascimento', 'sexo', 'utilizacao', 'endereco_cocheira'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    return True

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
    """Gera resposta do bot com validação melhorada"""
    try:
        # Verificar se quer atendimento humano
        needs_human = check_human_request(message)
        
        if needs_human:
            response = """👨‍💼 *Transferindo para atendimento humano...*

Entendi que voce precisa de ajuda personalizada.
Um de nossos especialistas ira atende-lo em breve.

Enquanto isso, pode continuar enviando as informacoes
do seu animal que ja vamos organizando tudo! 😊"""
            
            save_conversation_to_db(phone, message, response, 'bot', needs_human=True)
            return response
        
        # Buscar dados existentes
        client = get_client_data_from_db(phone)
        
        if client is None:
            conversation_count = 1
            existing_data = {}
        else:
            conversation_count = client.get('conversation_count', 0) + 1
            existing_data = client.get('data', {})
        
        # Extrair dados da mensagem
        updated_data = extract_animal_data_improved(message, existing_data)
        
        # Campos obrigatórios
        required_fields = {
            'nome_animal': 'Nome do Animal',
            'valor_animal': 'Valor do Animal (R$)',
            'registro': 'Numero de Registro ou Passaporte',
            'raca': 'Raca',
            'data_nascimento': 'Data de Nascimento',
            'sexo': 'Sexo (inteiro, castrado ou femea)',
            'utilizacao': 'Utilizacao (lazer, salto, laco, etc.)',
            'endereco_cocheira': 'Endereco da Cocheira (CEP e cidade)'
        }
        
        # Verificar campos
        missing_fields = []
        collected_fields = []
        
        for field_key, field_name in required_fields.items():
            if field_key in updated_data and updated_data[field_key]:
                collected_fields.append(f"✅ {field_name}: {updated_data[field_key]}")
            else:
                missing_fields.append(f"❌ {field_name}")
        
        # Verificar se todos os campos estão completos
        all_fields_complete = check_all_required_fields(updated_data)
        
        # Salvar dados
        status = 'completed' if all_fields_complete else 'collecting'
        save_client_data_to_db(phone, updated_data, status)
        
        # Se todos os campos estão completos, chamar automação SwissRe
        if all_fields_complete and status == 'completed':
            logger.info(f"🎯 Todos os dados completos para {phone} - Iniciando automação SwissRe")
            
            # Chamar automação SwissRe
            swissre_result = call_swissre_automation(updated_data)
            
            if swissre_result['success']:
                # Salvar cotação como completa
                save_quotation_to_db(phone, updated_data, swissre_result.get('pdf_url'), 'completed', 'bot')
                
                # Enviar PDF via WhatsApp
                if swissre_result.get('pdf_url'):
                    send_ultramsg_document(phone, swissre_result['pdf_url'], 
                                         "🎉 Sua cotacao de seguro equino esta pronta!")
                
                data_summary = "\\n".join(collected_fields)
                response = f"""🎉 *COTACAO FINALIZADA COM SUCESSO!*

{data_summary}

✅ *Sua proposta foi gerada e enviada!*

Nossa equipe processou todas as informacoes e sua
cotacao personalizada ja foi enviada via WhatsApp.

📋 *Proximos passos:*
• Analise a proposta recebida
• Entre em contato para duvidas
• Confirme a contratacao quando decidir

Obrigado por escolher a Equinos Seguros! 🐴✨"""
            else:
                # Erro na automação - salvar como falha
                save_quotation_to_db(phone, updated_data, None, 'failed', 'bot')
                
                response = f"""⚠️ *Dados completos coletados, mas houve um problema:*

{swissre_result['message']}

📞 *Nossa equipe foi notificada e entrara em contato
em breve para finalizar sua cotacao manualmente.*

Obrigado pela paciencia! 🙏"""
        
        # Gerar resposta normal se dados incompletos
        elif conversation_count == 1 or any(word in message.lower() for word in ['oi', 'ola', 'bom dia', 'inicio']):
            response = """🐴 *Ola! Bem-vindo a Equinos Seguros!*

Sou seu assistente virtual para cotacao de seguros equinos.

📋 *DADOS NECESSARIOS:*
• Nome do Animal
• Valor do Animal (R$) - ex: 50000 ou 50.000,00
• Numero de Registro ou Passaporte
• Raca - ex: Quarto de Milha, Mangalarga
• Data de Nascimento - formato: DD/MM/AAAA
• Sexo - inteiro, castrado ou femea
• Utilizacao - lazer, salto, laco, etc.
• Endereco da Cocheira - CEP e cidade completos

💡 *DICAS:*
• Pode enviar tudo de uma vez ou aos poucos
• Use formatos claros (ex: "Nome: Thor, Valor: 80000")
• Para ajuda humana, digite "falar com atendente"

Vamos comecar! 😊"""
        
        else:
            collected_list = "\\n".join(collected_fields) if collected_fields else "Nenhum dado coletado ainda."
            missing_list = "\\n".join(missing_fields[:4])
            
            response = f"""📝 *Obrigado pelas informacoes!*

*DADOS JA COLETADOS:*
{collected_list}

*AINDA PRECISO DE:*
{missing_list}

💡 *DICA:* Pode enviar varios dados juntos:
"Nome: Thor, Valor: 80000, Raca: Quarto de Milha"

Continue enviando! 😊"""
        
        # Salvar conversa
        save_conversation_to_db(phone, message, response, 'bot', needs_human=needs_human)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resposta: {str(e)}")
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
    """Lista todas as conversas"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Buscar conversas agrupadas por telefone
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
        
        return render_template_string(CONVERSATIONS_LIST_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    conversations=conversations_summary)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations/<phone>')
def agent_conversation_detail(phone):
    """Detalhes da conversa com portal de resposta"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        conversations = list(conversations_collection.find({"phone": phone}).sort("timestamp", 1))
        client_data = clients_collection.find_one({"phone": phone})
        
        return render_template_string(CONVERSATION_PORTAL_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    agent_email=session['agent_email'],
                                    phone=phone,
                                    conversations=conversations,
                                    client_data=client_data)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/send-message', methods=['POST'])
def agent_send_message():
    """Enviar mensagem pelo portal"""
    if 'agent_email' not in session:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        phone = request.form.get('phone')
        message = request.form.get('message')
        
        if not phone or not message:
            return jsonify({"error": "Telefone e mensagem são obrigatórios"}), 400
        
        # Enviar mensagem via UltraMsg
        success = send_ultramsg_message(phone, message)
        
        if success:
            # Salvar no banco como resposta humana
            save_conversation_to_db(phone, "", message, 'human', session['agent_email'])
            
            return jsonify({
                "success": True,
                "message": "Mensagem enviada com sucesso"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Erro ao enviar mensagem"
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
        pdf_url = request.form.get('pdf_url', '')
        
        if not phone:
            return jsonify({"error": "Telefone é obrigatório"}), 400
        
        # Buscar dados do cliente
        client = get_client_data_from_db(phone)
        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404
        
        # Salvar cotação como completa pelo humano
        save_quotation_to_db(phone, client.get('data', {}), pdf_url, 'completed', 'human', session['agent_email'])
        
        # Enviar mensagem de finalização
        completion_message = """🎉 *Cotacao finalizada por nosso especialista!*

Sua proposta personalizada foi processada e
sera enviada em breve.

Obrigado por escolher a Equinos Seguros! 🐴✨"""
        
        send_ultramsg_message(phone, completion_message)
        save_conversation_to_db(phone, "", completion_message, 'human', session['agent_email'])
        
        # Enviar PDF se fornecido
        if pdf_url:
            send_ultramsg_document(phone, pdf_url, "📋 Sua cotacao personalizada")
        
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

# Inicializar MongoDB ao iniciar
logger.info("🚀 Iniciando aplicação portal completo...")
init_mongodb()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando na porta {port}")
    logger.info(f"🗄️ MongoDB: {'Conectado' if mongodb_connected else 'Desconectado'}")
    logger.info(f"👥 Agentes configurados: {len(parse_agents_from_env())}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)