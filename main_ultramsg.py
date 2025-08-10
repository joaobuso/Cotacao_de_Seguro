# -*- coding: utf-8 -*-
"""
Arquivo principal do bot de cotação de seguros
Atualizado para usar UltraMsg no lugar do Twilio - Versão Melhorada
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, url_for
from dotenv import load_dotenv

# Importar módulos do projeto
from ultramsg_integration import ultramsg_api, send_whatsapp_message
from app.bot.handler_ultramsg import get_bot_response
from app.utils.audio_processor import convert_user_audio_to_text, generate_bot_audio_response
from app.utils.whatsapp_file_manager import send_pdf_to_whatsapp
from app.db.database import (
    save_message, get_conversation_status_and_id, set_conversation_status,
    SENDER_USER, SENDER_BOT, STATUS_BOT_ACTIVE, STATUS_AGENT_ACTIVE, STATUS_AWAITING_AGENT
)

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar app Flask
app = Flask(__name__, static_folder="static_bot_audio")

# Configurações
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-dev")
app.secret_key = FLASK_SECRET_KEY
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

# Palavras-chave que podem indicar um pedido de handoff
HANDOFF_KEYWORDS = [
    "atendente", "humano", "pessoa", "agente", "falar com alguém", 
    "falar com uma pessoa", "suporte", "ajuda humana", "operador"
]

def configure_routes(app):
    """Configura todas as rotas da aplicação"""
    
    @app.route("/", methods=["GET"])
    def home():
        """Página inicial"""
        return jsonify({
            "status": "success",
            "message": "Serviço de Webhook para WhatsApp com Cotação de Seguros está operacional!",
            "api": "UltraMsg",
            "version": "2.0",
            "endpoints": {
                "webhook": "/webhook/ultramsg",
                "health": "/health",
                "send_message": "/send-message",
                "send_document": "/send-document",
                "test": "/webhook/test"
            }
        })

    @app.route("/webhook/ultramsg", methods=["POST"])
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
            return process_incoming_message(phone_number, message_body, message_type, message_data)
            
        except Exception as e:
            logger.error(f"Erro no webhook UltraMsg: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/webhook", methods=["POST"])
    def twilio_webhook_compatibility():
        """
        Webhook de compatibilidade com Twilio (para migração gradual)
        """
        try:
            # Extrair dados do formato Twilio
            incoming_msg_text = request.values.get("Body", "").strip()
            phone_number = request.values.get("From", "")
            num_media = int(request.values.get("NumMedia", 0))
            media_url = None
            
            if num_media > 0:
                media_url = request.values.get("MediaUrl0")
                content_type = request.values.get("MediaContentType0", "")
                
                if "audio" in content_type:
                    message_type = "audio"
                else:
                    message_type = "media"
            else:
                message_type = "text"
            
            # Processar como mensagem UltraMsg
            return process_incoming_message(phone_number, incoming_msg_text, message_type, {"media_url": media_url})
            
        except Exception as e:
            logger.error(f"Erro no webhook Twilio: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def process_incoming_message(phone_number: str, message_body: str, message_type: str, message_data: dict):
        """
        Processa mensagem recebida independente da origem
        """
        try:
            user_message_processed = message_body
            media_url = message_data.get("media_url")
            
            # Processar mídia (áudio)
            if message_type == "audio" or (media_url and "audio" in str(media_url)):
                logger.info(f"Áudio recebido de {phone_number}: {media_url}")
                
                if media_url:
                    transcribed_text = convert_user_audio_to_text(media_url)
                    if transcribed_text:
                        user_message_processed = transcribed_text
                        logger.info(f"Áudio transcrito: {user_message_processed}")
                    else:
                        error_msg = "Desculpe, não consegui entender seu áudio. Por favor, tente novamente ou envie uma mensagem de texto."
                        send_whatsapp_message(phone_number, error_msg)
                        
                        # Salvar no banco
                        conversation_status, conversation_id = get_conversation_status_and_id(phone_number)
                        save_message(phone_number, SENDER_USER, "[Áudio não transcrito]", media_url=media_url, conversation_id=conversation_id)
                        save_message(phone_number, SENDER_BOT, error_msg, conversation_id=conversation_id)
                        
                        return jsonify({"status": "processed", "response": "audio_error"}), 200
                else:
                    user_message_processed = "[Áudio recebido sem URL]"
            
            elif message_type != "text" and media_url:
                # Outros tipos de mídia
                user_message_processed = f"[Mídia do tipo {message_type} recebida]"
                unsupported_media_msg = "Recebi uma mídia, mas só consigo processar mensagens de texto e áudio de voz."
                send_whatsapp_message(phone_number, unsupported_media_msg)
                
                # Salvar no banco
                conversation_status, conversation_id = get_conversation_status_and_id(phone_number)
                save_message(phone_number, SENDER_USER, user_message_processed, media_url=media_url, conversation_id=conversation_id)
                save_message(phone_number, SENDER_BOT, unsupported_media_msg, conversation_id=conversation_id)
                
                return jsonify({"status": "processed", "response": "unsupported_media"}), 200

            # Salvar mensagem do usuário
            conversation_status, conversation_id = get_conversation_status_and_id(phone_number)
            conversation_id = save_message(phone_number, SENDER_USER, user_message_processed, media_url=media_url, conversation_id=conversation_id)

            if not conversation_id:
                critical_error_msg = "Desculpe, estou enfrentando um problema técnico e não posso processar sua mensagem agora. Tente mais tarde."
                send_whatsapp_message(phone_number, critical_error_msg)
                return jsonify({"status": "error", "response": "database_error"}), 500

            # Lógica de Handoff e Resposta do Bot
            if conversation_status == STATUS_AGENT_ACTIVE or conversation_status == STATUS_AWAITING_AGENT:
                logger.info(f"Mensagem de {phone_number} para agente (status: {conversation_status}): {user_message_processed}")
                return jsonify({"status": "forwarded_to_agent"}), 200

            # Se BOT_ACTIVE, processar com o bot melhorado
            bot_reply_text, is_handoff_request, pdf_path = get_bot_response(
                user_message_processed, phone_number, conversation_id
            )

            if is_handoff_request:
                set_conversation_status(conversation_id, STATUS_AWAITING_AGENT)
                logger.info(f"Pedido de Handoff de {phone_number}. Status alterado para AWAITING_AGENT.")
            
            # Enviar resposta do bot (texto)
            text_result = send_whatsapp_message(phone_number, bot_reply_text)
            
            if text_result:
                logger.info(f"Resposta enviada para {phone_number}")
                # Salvar resposta do bot no BD
                save_message(phone_number, SENDER_BOT, bot_reply_text, conversation_id=conversation_id)
            else:
                logger.error(f"Erro ao enviar resposta para {phone_number}")

            # Tentar gerar e enviar áudio da resposta do bot
            try:
                audio_filename = generate_bot_audio_response(bot_reply_text)
                if audio_filename:
                    audio_url = url_for("static_audio_files", filename=audio_filename, _external=True)
                    if BASE_URL.startswith("https"): 
                        audio_url = audio_url.replace("http://", "https://", 1)

                    # Enviar áudio via UltraMsg
                    audio_result = ultramsg_api.send_audio(phone_number, audio_url)
                    
                    if audio_result.get("success"):
                        logger.info(f"Áudio da resposta do bot enviado: {audio_url}")
                    else:
                        logger.warning(f"Erro ao enviar áudio: {audio_result.get('error')}")
                        
            except Exception as e:
                logger.warning(f"Erro ao processar áudio da resposta: {str(e)}")

            # Enviar PDF se disponível
            if pdf_path:
                try:
                    pdf_result = send_pdf_to_whatsapp(phone_number, pdf_path)
                    if pdf_result:
                        logger.info(f"PDF enviado para {phone_number}: {pdf_path}")
                    else:
                        logger.error(f"Erro ao enviar PDF para {phone_number}")
                except Exception as e:
                    logger.error(f"Erro ao enviar PDF: {str(e)}")

            return jsonify({
                "status": "processed", 
                "response": "success",
                "text_sent": text_result,
                "handoff_requested": is_handoff_request
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/send-message", methods=["POST"])
    def send_message():
        """
        Endpoint para enviar mensagens manualmente
        """
        try:
            data = request.get_json()
            phone = data.get("phone")
            message = data.get("message")
            
            if not phone or not message:
                return jsonify({"error": "Phone and message are required"}), 400
            
            result = send_whatsapp_message(phone, message)
            
            return jsonify({
                "success": result,
                "phone": phone,
                "message": message
            }), 200 if result else 400
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem manual: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/send-document", methods=["POST"])
    def send_document():
        """
        Endpoint para enviar documentos (PDFs de cotação)
        """
        try:
            data = request.get_json()
            phone = data.get("phone")
            document_url = data.get("document_url")
            filename = data.get("filename", "cotacao.pdf")
            caption = data.get("caption", "")
            
            if not phone or not document_url:
                return jsonify({"error": "Phone and document_url are required"}), 400
            
            result = ultramsg_api.send_document(phone, document_url, filename, caption)
            
            return jsonify(result), 200 if result.get("success") else 400
            
        except Exception as e:
            logger.error(f"Erro ao enviar documento: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/test", methods=["POST", "GET"])
    def test_webhook():
        """
        Endpoint para testar o webhook
        """
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
            
            # Simular processamento
            phone_number = test_data["data"]["from"]
            message_body = test_data["data"]["body"]
            
            # Processar mensagem de teste
            conversation_status, conversation_id = get_conversation_status_and_id(phone_number)
            bot_reply_text, is_handoff_request, pdf_path = get_bot_response(
                message_body, phone_number, conversation_id
            )
            
            return jsonify({
                "status": "test_success",
                "test_data": test_data,
                "bot_response": bot_reply_text,
                "handoff_requested": is_handoff_request,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "conversation_status": conversation_status
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no teste: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        """Endpoint para verificação de saúde do serviço"""
        try:
            # Verificar status da instância UltraMsg
            ultramsg_status = ultramsg_api.get_instance_status()
            
            return jsonify({
                "status": "healthy",
                "service": "whatsapp-insurance-bot",
                "api": "UltraMsg",
                "ultramsg_status": ultramsg_status.get("success", False),
                "timestamp": str(datetime.now())
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no health check: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500

    # Rota para servir os arquivos de áudio cacheados do bot
    @app.route("/static_audio/<path:filename>")
    def static_audio_files(filename):
        """Serve arquivos de áudio estáticos"""
        return send_from_directory(app.static_folder, filename)
    
    # Rota para servir arquivos estáticos (PDFs, etc.)
    @app.route("/static_files/<path:filename>")
    def static_files(filename):
        """Serve arquivos estáticos (PDFs, documentos)"""
        static_files_dir = os.path.join(app.root_path, "static_files")
        return send_from_directory(static_files_dir, filename)

# Configurar rotas
configure_routes(app)

# Registrar blueprint do painel de agente (se existir)
try:
    from app.agent.routes import agent_bp
    app.register_blueprint(agent_bp)
    logger.info("Painel de agente registrado com sucesso")
except ImportError:
    logger.warning("Painel de agente não encontrado - continuando sem ele")

if __name__ == "__main__":
    # Criar diretórios necessários
    static_audio_dir = os.path.join(os.path.dirname(__file__), "static_bot_audio")
    static_files_dir = os.path.join(os.path.dirname(__file__), "static_files")
    os.makedirs(static_audio_dir, exist_ok=True)
    os.makedirs(static_files_dir, exist_ok=True)
    
    # Configurações do servidor
    PORT = int(os.getenv("PORT", 8080))
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"Iniciando servidor Flask na porta {PORT}")
    logger.info(f"Webhook UltraMsg: {BASE_URL}/webhook/ultramsg")
    logger.info(f"Debug mode: {DEBUG}")
    
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)

