import os
from flask import request, send_from_directory, url_for
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Importar módulos do projeto
from .db import database
from .bot import handler as bot_handler
from .utils import audio_processor

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Função para configurar as rotas na aplicação Flask
def configure_routes(app):
    # Configurações
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-dev")
    app.secret_key = FLASK_SECRET_KEY
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
    
    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():
        twilio_resp = MessagingResponse()
        incoming_msg_text = request.values.get("Body", "").strip()
        phone_number = request.values.get("From", "")
        num_media = int(request.values.get("NumMedia", 0))
        media_url = None
        user_message_processed = incoming_msg_text

        if not phone_number:
            return "Webhook Error: Missing sender information", 400

        if num_media > 0:
            media_url = request.values.get("MediaUrl0")
            content_type = request.values.get("MediaContentType0", "")
            if "audio" in content_type:
                print(f"Áudio recebido de {phone_number}: {media_url}")
                transcribed_text = audio_processor.convert_user_audio_to_text(media_url)
                if transcribed_text:
                    user_message_processed = transcribed_text
                    print(f"Áudio transcrito: {user_message_processed}")
                else:
                    error_msg = "Desculpe, não consegui entender seu áudio. Por favor, tente novamente ou envie uma mensagem de texto."
                    twilio_resp.message(error_msg)
                    database.save_message(phone_number, database.SENDER_USER, "[Áudio não transcrito]", media_url=media_url)
                    database.save_message(phone_number, database.SENDER_BOT, error_msg)
                    return str(twilio_resp)
            else:
                user_message_processed = f"[Mídia do tipo {content_type} recebida, não processada]"
                database.save_message(phone_number, database.SENDER_USER, user_message_processed, media_url=media_url)
                unsupported_media_msg = "Recebi uma mídia, mas só consigo processar mensagens de texto e áudio de voz."
                twilio_resp.message(unsupported_media_msg)
                database.save_message(phone_number, database.SENDER_BOT, unsupported_media_msg)
                return str(twilio_resp)

        # Salvar mensagem do usuário
        conversation_status, conversation_id = database.get_conversation_status_and_id(phone_number)
        conversation_id = database.save_message(phone_number, database.SENDER_USER, user_message_processed, media_url=media_url, conversation_id=conversation_id)

        if not conversation_id:
            critical_error_msg = "Desculpe, estou enfrentando um problema técnico e não posso processar sua mensagem agora. Tente mais tarde."
            twilio_resp.message(critical_error_msg)
            return str(twilio_resp)

        # Lógica de Handoff e Resposta do Bot
        if conversation_status == database.STATUS_AGENT_ACTIVE or conversation_status == database.STATUS_AWAITING_AGENT:
            print(f"Mensagem de {phone_number} para agente (status: {conversation_status}): {user_message_processed}")
            return str(twilio_resp)

        # Se BOT_ACTIVE, processar com o bot
        bot_reply_text, is_handoff_request = bot_handler.get_bot_response(user_message_processed)

        if is_handoff_request:
            database.set_conversation_status(conversation_id, database.STATUS_AWAITING_AGENT)
            print(f"Pedido de Handoff de {phone_number}. Status alterado para AWAITING_AGENT.")
        
        # Enviar resposta do bot (texto)
        twilio_resp.message(bot_reply_text)
        # Salvar resposta do bot no BD
        database.save_message(phone_number, database.SENDER_BOT, bot_reply_text, conversation_id=conversation_id)

        # Tentar gerar e enviar áudio da resposta do bot
        # Tentar gerar e enviar áudio da resposta do bot
        audio_filename = audio_processor.generate_bot_audio_response(bot_reply_text)
        if audio_filename:
            audio_url = url_for("static_audio_files", filename=audio_filename, _external=True)
            if BASE_URL.startswith("https"): 
                audio_url = audio_url.replace("http://", "https://", 1)

            # Criar nova mensagem e anexar mídia corretamente
            audio_message_tag = twilio_resp.message()
            audio_message_tag.media(audio_url)
            print(f"Áudio da resposta do bot enviado: {audio_url}")

        return str(twilio_resp)

    # Rota para servir os arquivos de áudio cacheados do bot
    @app.route("/static_audio/<path:filename>")
    def static_audio_files(filename):
        return send_from_directory(app.static_folder, filename)

    @app.route("/")
    def home():
        return "Serviço de Webhook para WhatsApp Handoff está operacional!", 200

# Esta parte só será executada se o arquivo for executado diretamente, não quando importado
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__, static_folder="static_bot_audio")
    configure_routes(app)
    
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    
    print(f"Iniciando Flask app em modo de desenvolvimento.")
    print(f"Para testar o webhook, configure o Twilio para POST em http://localhost:{PORT}/webhook")
    
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
