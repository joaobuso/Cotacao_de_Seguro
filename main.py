# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - Versão Final Melhorada
"""

import os
import logging
import requests
import urllib.parse
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from dotenv import load_dotenv
import hashlib

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

# Tentar conectar MongoDB
def init_mongodb():
    global mongodb_connected, mongo_client, db, conversations_collection, clients_collection, agents_collection
    
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
            'needs_human': needs_human,  # Flag para atendimento humano
            'timestamp': datetime.utcnow(),
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'time': datetime.utcnow().strftime('%H:%M:%S')
        }
        
        conversations_collection.insert_one(conversation)
        logger.info(f"💾 Conversa salva: {phone} - Humano: {needs_human}")
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
        
        logger.info(f"💾 Cliente salvo: {phone}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cliente: {str(e)}")
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
            r'animal[:\s]*([a-záêçõã\s]+?)(?:\s|$|,|\.|;)',
            r'^([a-záêçõã\s]+?)(?:\s|$|,|\.|;)'  # Primeira palavra se for nome
        ],
        'valor_animal': [
            r'valor[:\s]*r?\$?\s*([0-9.,]+)',
            r'vale[:\s]*r?\$?\s*([0-9.,]+)',
            r'custa[:\s]*r?\$?\s*([0-9.,]+)',
            r'preco[:\s]*r?\$?\s*([0-9.,]+)',
            r'r\$\s*([0-9.,]+)',
            r'([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',  # Formato brasileiro
            r'([0-9]+\.?[0-9]*\.?[0-9]*)'  # Números com pontos
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
            r'([0-9]{4,8})'  # Números de 4-8 dígitos
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
            r'([0-9]{5}[\-\s]?[0-9]{3})',  # CEP
            r'([a-záêçõã\s]+\s+[a-z]{2})'  # Cidade + Estado
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
                        # Limpar e formatar valor
                        value = re.sub(r'[^\d.,]', '', value)
                        if value and len(value) >= 3:  # Valor mínimo
                            data[field] = value
                    elif field == 'nome_animal':
                        # Validar nome (não pode ser muito curto ou números)
                        if len(value) >= 2 and not value.isdigit() and not re.match(r'^[0-9.,]+$', value):
                            data[field] = value.title()
                    elif field == 'data_nascimento':
                        # Validar formato de data
                        if re.match(r'[0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4}', value):
                            data[field] = value
                    elif field == 'endereco_cocheira':
                        # Validar endereço (mínimo 5 caracteres)
                        if len(value) >= 5:
                            data[field] = value
                    else:
                        data[field] = value
                    
                    break
    
    return data

def validate_field_format(field, value):
    """Valida formato de campos específicos"""
    errors = []
    
    if field == 'valor_animal':
        if not re.match(r'^[0-9.,]+$', str(value)):
            errors.append("Valor deve conter apenas numeros (ex: 50000 ou 50.000,00)")
        elif float(re.sub(r'[^\d]', '', str(value))) < 1000:
            errors.append("Valor muito baixo. Minimo R$ 1.000")
    
    elif field == 'data_nascimento':
        if not re.match(r'^[0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4}$', str(value)):
            errors.append("Data deve estar no formato DD/MM/AAAA (ex: 15/06/2010)")
    
    elif field == 'registro':
        if len(str(value)) < 4:
            errors.append("Numero de registro deve ter pelo menos 4 caracteres")
    
    elif field == 'endereco_cocheira':
        if len(str(value)) < 10:
            errors.append("Endereco deve ser mais completo (CEP e cidade)")
    
    elif field == 'nome_animal':
        if len(str(value)) < 2:
            errors.append("Nome do animal deve ter pelo menos 2 caracteres")
        elif str(value).isdigit():
            errors.append("Nome do animal nao pode ser apenas numeros")
    
    return errors

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
        
        # Validar campos e gerar feedback
        validation_errors = []
        missing_fields = []
        collected_fields = []
        
        for field_key, field_name in required_fields.items():
            if field_key in updated_data and updated_data[field_key]:
                # Validar formato
                errors = validate_field_format(field_key, updated_data[field_key])
                if errors:
                    validation_errors.extend([f"❌ {field_name}: {error}" for error in errors])
                    # Remove campo inválido
                    del updated_data[field_key]
                    missing_fields.append(f"❌ {field_name}")
                else:
                    collected_fields.append(f"✅ {field_name}: {updated_data[field_key]}")
            else:
                missing_fields.append(f"❌ {field_name}")
        
        # Salvar dados
        status = 'completed' if len(missing_fields) == 0 else 'collecting'
        save_client_data_to_db(phone, updated_data, status)
        
        # Gerar resposta
        message_lower = message.lower()
        
        if conversation_count == 1 or any(word in message_lower for word in ['oi', 'ola', 'bom dia', 'inicio']):
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
        
        elif validation_errors:
            # Há erros de formato
            errors_text = "\\n".join(validation_errors)
            response = f"""⚠️ *Encontrei alguns problemas nos dados:*

{errors_text}

📝 *EXEMPLOS CORRETOS:*
• Valor: 50000 ou 50.000,00
• Data: 15/06/2010
• Endereco: Rua das Flores 123, CEP 12345-678, Campinas SP

Por favor, envie novamente com o formato correto! 😊"""
        
        elif len(missing_fields) == 0:
            data_summary = "\\n".join(collected_fields)
            response = f"""✅ *PERFEITO! Dados completos coletados:*

{data_summary}

🎉 *Sua cotacao esta sendo processada!*

Nossa equipe ira analisar as informacoes e enviar
sua proposta personalizada em breve.

Obrigado por escolher a Equinos Seguros! 🐴✨"""
        
        else:
            collected_list = "\\n".join(collected_fields) if collected_fields else "Nenhum dado coletado ainda."
            missing_list = "\\n".join(missing_fields[:4])  # Mostrar só os 4 primeiros
            
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
        "service": "Bot Cotacao Seguros - Versao Final",
        "version": "3.0.0",
        "timestamp": str(datetime.utcnow()),
        "mongodb_connected": mongodb_connected,
        "ultramsg_instance": ULTRAMSG_INSTANCE_ID,
        "agents_configured": len(agents_info),
        "features": [
            "Bot inteligente com validacao",
            "Captura melhorada de dados",
            "Agentes via environment variables",
            "Painel simplificado bot vs humano",
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
                "human_needed": conversations_collection.count_documents({"needs_human": True}),
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

# PAINEL DE AGENTES SIMPLIFICADO

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
    """Dashboard simplificado"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Estatísticas focadas em bot vs humano
        stats = {
            "total_clients": clients_collection.count_documents({}),
            "bot_handled": conversations_collection.count_documents({"message_type": "bot", "needs_human": False}),
            "human_needed": conversations_collection.count_documents({"needs_human": True}),
            "pending_human": conversations_collection.count_documents({"needs_human": True, "message_type": "bot"}),
            "today_conversations": conversations_collection.count_documents({
                "date": datetime.utcnow().strftime('%Y-%m-%d')
            })
        }
        
        # Conversas que precisam de atendimento humano
        human_needed = list(conversations_collection.find({"needs_human": True}).sort("timestamp", -1).limit(10))
        
        return render_template_string(DASHBOARD_SIMPLE_TEMPLATE, 
                                    agent_name=session['agent_name'],
                                    stats=stats,
                                    human_needed=human_needed)
    
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/human-needed')
def agent_human_needed():
    """Lista conversas que precisam de atendimento humano"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        # Buscar conversas que precisam de humano
        pipeline = [
            {"$match": {"needs_human": True}},
            {"$group": {
                "_id": "$phone",
                "last_message": {"$last": "$message"},
                "last_timestamp": {"$last": "$timestamp"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"last_timestamp": -1}}
        ]
        
        human_clients = list(conversations_collection.aggregate(pipeline))
        
        return render_template_string(HUMAN_NEEDED_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    human_clients=human_clients)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

@app.route('/agent/conversations/<phone>')
def agent_conversation_detail(phone):
    """Detalhes da conversa"""
    if 'agent_email' not in session:
        return redirect(url_for('agent_login'))
    
    if not mongodb_connected:
        return "MongoDB não conectado", 500
    
    try:
        conversations = list(conversations_collection.find({"phone": phone}).sort("timestamp", 1))
        client_data = clients_collection.find_one({"phone": phone})
        
        return render_template_string(CONVERSATION_DETAIL_SIMPLE_TEMPLATE,
                                    agent_name=session['agent_name'],
                                    phone=phone,
                                    conversations=conversations,
                                    client_data=client_data)
    
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return f"Erro: {str(e)}", 500

# TEMPLATES HTML SIMPLIFICADOS

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Painel de Agentes</title>
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
        <h1>🤖 Painel de Agentes</h1>
        <h3>Equinos Seguros - Bot vs Humano</h3>
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

DASHBOARD_SIMPLE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Bot vs Humano - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 32px; font-weight: bold; }
        .stat-label { color: #666; margin-top: 5px; }
        .bot-stat { color: #28a745; }
        .human-stat { color: #dc3545; }
        .pending-stat { color: #ffc107; }
        .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px; }
        .btn-danger { background: #dc3545; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .urgent { border-left: 4px solid #dc3545; }
        .conversation { border-bottom: 1px solid #eee; padding: 15px 0; }
        .phone { font-weight: bold; color: #007bff; }
        .message { color: #666; margin: 5px 0; }
        .timestamp { font-size: 12px; color: #999; }
        .human-flag { background: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 vs 👨‍💼 Dashboard - {{ agent_name }}</h1>
        <div>
            <a href="/agent/human-needed" class="btn btn-danger">🚨 Atendimento Humano ({{ stats.human_needed }})</a>
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
                <div class="stat-number bot-stat">{{ stats.bot_handled }}</div>
                <div class="stat-label">🤖 Resolvido pelo Bot</div>
            </div>
            <div class="stat-card">
                <div class="stat-number human-stat">{{ stats.human_needed }}</div>
                <div class="stat-label">👨‍💼 Precisa de Humano</div>
            </div>
            <div class="stat-card">
                <div class="stat-number pending-stat">{{ stats.pending_human }}</div>
                <div class="stat-label">⏳ Aguardando Atendimento</div>
            </div>
        </div>
        
        {% if human_needed %}
        <div class="section urgent">
            <h3>🚨 Conversas que Precisam de Atendimento Humano</h3>
            {% for conv in human_needed %}
            <div class="conversation">
                <div class="phone">📱 {{ conv.phone }} <span class="human-flag">HUMANO</span></div>
                <div class="message">"{{ conv.message[:100] }}..."</div>
                <div class="timestamp">{{ conv.timestamp.strftime('%d/%m/%Y %H:%M') }}</div>
                <div style="margin-top: 10px;">
                    <a href="/agent/conversations/{{ conv.phone }}" class="btn">Ver Conversa</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="section">
            <h3>📊 Resumo de Performance</h3>
            <p><strong>Taxa de Resolução do Bot:</strong> 
            {% if stats.bot_handled + stats.human_needed > 0 %}
                {{ "%.1f"|format((stats.bot_handled / (stats.bot_handled + stats.human_needed)) * 100) }}%
            {% else %}
                0%
            {% endif %}
            </p>
            <p><strong>Conversas Hoje:</strong> {{ stats.today_conversations }}</p>
        </div>
    </div>
</body>
</html>
"""

HUMAN_NEEDED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Atendimento Humano Necessário - {{ agent_name }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .header { background: #dc3545; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { padding: 20px; }
        .client-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; border-left: 4px solid #dc3545; }
        .client-phone { font-size: 18px; font-weight: bold; color: #dc3545; margin-bottom: 10px; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .btn-back { background: #6c757d; }
        .urgent-badge { background: #dc3545; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Atendimento Humano Necessário</h1>
        <div>
            <a href="/agent/dashboard" class="btn btn-back">⬅ Dashboard</a>
            <a href="/agent/logout" class="btn">🚪 Sair</a>
        </div>
    </div>
    
    <div class="container">
        <div style="margin-bottom: 20px;">
            <span class="urgent-badge">{{ human_clients|length }} clientes aguardando</span>
        </div>
        
        {% for client in human_clients %}
        <div class="client-card">
            <div class="client-phone">📱 {{ client._id }}</div>
            <div style="margin-bottom: 10px;">
                <strong>Última mensagem:</strong> "{{ client.last_message[:150] }}..."
            </div>
            <div style="margin-bottom: 15px; color: #666;">
                <strong>Última atividade:</strong> {{ client.last_timestamp.strftime('%d/%m/%Y %H:%M') }}
            </div>
            <div>
                <a href="/agent/conversations/{{ client._id }}" class="btn">👀 Ver Conversa Completa</a>
            </div>
        </div>
        {% endfor %}
        
        {% if not human_clients %}
        <div style="text-align: center; padding: 40px; color: #666;">
            <h3>🎉 Nenhum atendimento humano pendente!</h3>
            <p>Todos os clientes estão sendo bem atendidos pelo bot.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

CONVERSATION_DETAIL_SIMPLE_TEMPLATE = """
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
        .message { margin-bottom: 15px; padding: 15px; border-radius: 8px; }
        .message-user { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .message-bot { background: #f1f8e9; border-left: 4px solid #4caf50; }
        .message-human-needed { background: #fff3e0; border-left: 4px solid #ff9800; }
        .message-header { font-weight: bold; margin-bottom: 8px; }
        .message-content { margin-bottom: 8px; line-height: 1.4; }
        .message-timestamp { font-size: 12px; color: #666; }
        .btn { padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .human-flag { background: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 10px; }
        .field { margin-bottom: 10px; }
        .field-label { font-weight: bold; color: #333; }
        .field-value { color: #666; margin-top: 2px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💬 Conversa: {{ phone }}</h1>
        <div>
            <a href="/agent/human-needed" class="btn">⬅ Voltar</a>
        </div>
    </div>
    
    <div class="container">
        <div class="conversation-panel">
            <h3>📱 Histórico da Conversa</h3>
            {% for conv in conversations %}
            <div class="message {% if conv.needs_human %}message-human-needed{% elif loop.index0 % 2 == 0 %}message-user{% else %}message-bot{% endif %}">
                <div class="message-header">
                    {% if loop.index0 % 2 == 0 %}
                        👤 Cliente
                    {% else %}
                        🤖 Bot
                    {% endif %}
                    {% if conv.needs_human %}
                        <span class="human-flag">QUER HUMANO</span>
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
            <h3>📋 Dados Coletados</h3>
            {% if client_data and client_data.data %}
            {% for key, value in client_data.data.items() %}
            <div class="field">
                <div class="field-label">{{ key.replace('_', ' ').title() }}:</div>
                <div class="field-value">{{ value }}</div>
            </div>
            {% endfor %}
            <div class="field">
                <div class="field-label">Status:</div>
                <div class="field-value">{{ client_data.status }}</div>
            </div>
            {% else %}
            <p>Nenhum dado coletado ainda.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# Inicializar MongoDB ao iniciar
logger.info("🚀 Iniciando aplicação melhorada...")
init_mongodb()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando na porta {port}")
    logger.info(f"🗄️ MongoDB: {'Conectado' if mongodb_connected else 'Desconectado'}")
    logger.info(f"👥 Agentes configurados: {len(parse_agents_from_env())}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
