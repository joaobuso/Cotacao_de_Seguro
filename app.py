# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros para Equinos - UltraMsg
Aplicação principal Flask
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, url_for, session
from dotenv import load_dotenv

# Importar módulos do projeto
from app.integrations.ultramsg_api import ultramsg_api
from app.bot.message_handler import MessageHandler
from app.db.database import Database
from app.utils.audio_processor import AudioProcessor
from app.utils.file_manager import FileManager

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
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Inicializar componentes
message_handler = MessageHandler()
database = Database()
audio_processor = AudioProcessor()
file_manager = FileManager()

# Configurações
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8080')

@app.route('/', methods=['GET'])
def home():
    """Página inicial da aplicação"""
    return jsonify({
        "status": "success",
        "message": "🤖 Bot de Cotação de Seguros para Equinos",
        "api": "UltraMsg",
        "version": "2.0",
        "endpoints": {
            "webhook": "/webhook/ultramsg",
            "health": "/health",
            "send_message": "/api/send-message",
            "send_document": "/api/send-document",
            "agent_login": "/agent/login",
            "agent_dashboard": "/agent/dashboard"
        },
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/webhook/ultramsg', methods=['POST'])
def ultramsg_webhook():
    """
    Webhook principal para receber mensagens do UltraMsg
    """
    try:
        # Obter dados da requisição
        data = request.get_json()
        
        if not data:
            logger.warning("Webhook recebido sem dados JSON")
            return jsonify({"status": "ignored", "reason": "no_data"}), 200
        
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Verificar se é mensagem recebida
        event_type = data.get("event")
        if event_type != "message":
            logger.info(f"Evento ignorado: {event_type}")
            return jsonify({"status": "ignored", "reason": "not_message"}), 200
        
        # Extrair dados da mensagem
        message_data = data.get("data", {})
        phone_number = message_data.get("from", "")
        message_body = message_data.get("body", "")
        message_type = message_data.get("type", "text")
        
        # Verificar se é mensagem própria (enviada pelo bot)
        if message_data.get("fromMe", False):
            logger.info("Mensagem própria ignorada")
            return jsonify({"status": "ignored", "reason": "own_message"}), 200
        
        # Ignorar mensagens vazias ou sem remetente
        if not phone_number or not message_body:
            logger.warning(f"Mensagem inválida - Phone: {phone_number}, Body: {message_body}")
            return jsonify({"status": "ignored", "reason": "invalid_message"}), 200
        
        # Processar mensagem
        result = message_handler.process_message(phone_number, message_body, message_type, message_data)
        
        return jsonify({
            "status": "processed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no webhook UltraMsg: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Endpoint para enviar mensagens manualmente"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        message = data.get("message")
        
        if not phone or not message:
            return jsonify({"error": "Phone and message are required"}), 400
        
        result = ultramsg_api.send_text_message(phone, message)
        
        return jsonify({
            "success": result.get("success", False),
            "phone": phone,
            "message": message,
            "result": result
        }), 200 if result.get("success") else 400
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem manual: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/send-document', methods=['POST'])
def send_document():
    """Endpoint para enviar documentos"""
    try:
        data = request.get_json()
        phone = data.get("phone")
        document_url = data.get("document_url")
        filename = data.get("filename", "documento.pdf")
        caption = data.get("caption", "")
        
        if not phone or not document_url:
            return jsonify({"error": "Phone and document_url are required"}), 400
        
        result = ultramsg_api.send_document(phone, document_url, filename, caption)
        
        return jsonify(result), 200 if result.get("success") else 400
        
    except Exception as e:
        logger.error(f"Erro ao enviar documento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificação de saúde do serviço"""
    try:
        # Verificar status da instância UltraMsg
        ultramsg_status = ultramsg_api.get_instance_status()
        
        # Verificar conexão com banco de dados
        db_status = database.check_connection()
        
        return jsonify({
            "status": "healthy",
            "service": "whatsapp-insurance-bot",
            "api": "UltraMsg",
            "components": {
                "ultramsg": ultramsg_status.get("success", False),
                "database": db_status,
                "audio_processor": True,
                "file_manager": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/webhook/test', methods=['POST', 'GET'])
def test_webhook():
    """Endpoint para testar o webhook"""
    try:
        # Dados de teste
        test_data = {
            "event": "message",
            "data": {
                "from": "+5519988118043",
                "body": "Olá, quero fazer uma cotação de seguro para meu cavalo",
                "type": "text",
                "fromMe": False
            }
        }
        
        # Processar mensagem de teste
        phone_number = test_data["data"]["from"]
        message_body = test_data["data"]["body"]
        
        result = message_handler.process_message(phone_number, message_body, "text", test_data["data"])
        
        return jsonify({
            "status": "test_success",
            "test_data": test_data,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Rota para servir arquivos de áudio
@app.route('/static_audio/<path:filename>')
def static_audio_files(filename):
    """Serve arquivos de áudio estáticos"""
    return send_from_directory('static_bot_audio', filename)

# Rota para servir arquivos estáticos (PDFs, documentos)
@app.route('/static_files/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos (PDFs, documentos)"""
    return send_from_directory('static_files', filename)

# Registrar blueprint do painel de agente
try:
    from app.agent.routes import agent_bp
    app.register_blueprint(agent_bp)
    logger.info("✅ Painel de agente registrado com sucesso")
except ImportError as e:
    logger.warning(f"⚠️ Painel de agente não encontrado: {e}")

if __name__ == "__main__":
    # Criar diretórios necessários
    os.makedirs('static_bot_audio', exist_ok=True)
    os.makedirs('static_files', exist_ok=True)
    
    # Configurações do servidor
    PORT = int(os.getenv("PORT", 8080))
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"🚀 Iniciando servidor Flask na porta {PORT}")
    logger.info(f"📡 Webhook UltraMsg: {BASE_URL}/webhook/ultramsg")
    logger.info(f"🔧 Debug mode: {DEBUG}")
    
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)

