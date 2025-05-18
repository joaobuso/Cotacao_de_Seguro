# /home/ubuntu/whatsapp_handoff_project/app/main.py
import os
from flask import Flask, request, send_from_directory, url_for
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Importar módulos do projeto
from .db import database
from .bot import handler as bot_handler
from .utils import audio_processor
# from .utils import notifications # Descomentar quando as notificações forem implementadas

# Carregar variáveis de ambiente do arquivo .env na raiz do projeto
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__, static_folder="static_bot_audio") # Servirá áudios da pasta static_bot_audio

# Configurações (podem vir do .env também)
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-dev")
app.secret_key = FLASK_SECRET_KEY
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000") # Necessário para URLs de áudio

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    twilio_resp = MessagingResponse()
    incoming_msg_text = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "")
    num_media = int(request.values.get("NumMedia", 0))
    media_url = None
    user_message_processed = incoming_msg_text

    if not phone_number:
        # Não deve acontecer com Twilio, mas é uma boa verificação
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
                # Falha na transcrição, envia mensagem de erro e não processa mais
                error_msg = "Desculpe, não consegui entender seu áudio. Por favor, tente novamente ou envie uma mensagem de texto."
                twilio_resp.message(error_msg)
                database.save_message(phone_number, database.SENDER_USER, "[Áudio não transcrito]", media_url=media_url)
                database.save_message(phone_number, database.SENDER_BOT, error_msg)
                return str(twilio_resp)
        else:
            # Mídia não suportada (ex: imagem, vídeo)
            user_message_processed = f"[Mídia do tipo {content_type} recebida, não processada]"
            # Salva a informação de que uma mídia foi recebida
            database.save_message(phone_number, database.SENDER_USER, user_message_processed, media_url=media_url)
            # Informa ao usuário que a mídia não é processada pelo bot (exceto áudio)
            unsupported_media_msg = "Recebi uma mídia, mas só consigo processar mensagens de texto e áudio de voz."
            twilio_resp.message(unsupported_media_msg)
            database.save_message(phone_number, database.SENDER_BOT, unsupported_media_msg)
            return str(twilio_resp)

    # Salvar mensagem do usuário (original ou transcrita)
    conversation_status, conversation_id = database.get_conversation_status_and_id(phone_number)
    # Garante que conversation_id seja criado se não existir ao salvar a primeira mensagem
    conversation_id = database.save_message(phone_number, database.SENDER_USER, user_message_processed, media_url=media_url, conversation_id=conversation_id)

    if not conversation_id:
        # Falha crítica ao salvar/criar conversa
        critical_error_msg = "Desculpe, estou enfrentando um problema técnico e não posso processar sua mensagem agora. Tente mais tarde."
        twilio_resp.message(critical_error_msg)
        return str(twilio_resp)

    # Lógica de Handoff e Resposta do Bot
    if conversation_status == database.STATUS_AGENT_ACTIVE or conversation_status == database.STATUS_AWAITING_AGENT:
        # Mensagem para agente, não fazer nada aqui além de salvar (já feito)
        # A interface do agente lidará com a notificação e resposta
        print(f"Mensagem de {phone_number} para agente (status: {conversation_status}): {user_message_processed}")
        # Não enviar resposta automática do bot
        return str(twilio_resp) # Twilio espera uma resposta, mesmo que vazia

    # Se BOT_ACTIVE, processar com o bot
    bot_reply_text, is_handoff_request = bot_handler.get_bot_response(user_message_processed)

    if is_handoff_request:
        database.set_conversation_status(conversation_id, database.STATUS_AWAITING_AGENT)
        # notifications.notify_agents_new_request(conversation_id, phone_number, user_message_processed) # Descomentar quando implementado
        print(f"Pedido de Handoff de {phone_number}. Status alterado para AWAITING_AGENT.")
    
    # Enviar resposta do bot (texto)
    twilio_resp.message(bot_reply_text)
    # Salvar resposta do bot no BD
    database.save_message(phone_number, database.SENDER_BOT, bot_reply_text, conversation_id=conversation_id)

    # Tentar gerar e enviar áudio da resposta do bot
    # A URL base para os áudios precisa ser acessível publicamente (ngrok em dev, domínio em prod)
    audio_filename = audio_processor.generate_bot_audio_response(bot_reply_text)
    if audio_filename:
        # Constrói a URL completa para o arquivo de áudio
        # A pasta "static_bot_audio" é servida pela rota /static_audio/
        audio_url = url_for("static_audio_files", filename=audio_filename, _external=True)
        # Garante que a URL está usando HTTPS se o BASE_URL estiver em HTTPS (importante para Twilio)
        if BASE_URL.startswith("https"): 
            audio_url = audio_url.replace("http://", "https://", 1)
        
        # Adiciona a mídia à resposta do Twilio
        # Twilio envia mensagens separadas para texto e mídia se ambos estiverem no mesmo <Response>
        # Para enviar texto e áudio juntos, o ideal é que o texto seja a transcrição do áudio.
        # Como já enviamos o texto, podemos enviar o áudio como uma mensagem subsequente (Twilio pode juntar ou não)
        # Ou, se o bot_reply_text for a transcrição exata, podemos apenas enviar o áudio.
        # Por simplicidade, vamos enviar o áudio como uma mensagem de mídia separada na TwiML.
        # Twilio_resp.message().media(audio_url) # Isso criaria uma nova mensagem só com áudio.
        
        # Para evitar mensagens duplicadas se o texto já foi enviado, criamos uma nova mensagem TwiML para o áudio
        # No entanto, a prática comum é enviar o texto e, se o áudio for a fala desse texto, o usuário recebe ambos.
        # Se o objetivo é enviar o áudio *em vez* do texto, a lógica seria diferente.
        # Vamos assumir que o usuário recebe o texto e o áudio.
        # Se o texto já foi adicionado à twilio_resp, adicionar mídia pode resultar em duas mensagens.
        # A documentação do Twilio sugere que texto e mídia em um mesmo <Message> são suportados.
        # Vamos tentar adicionar ao mesmo <Message> se possível, ou criar um novo.
        
        # A forma mais simples é criar uma nova mensagem para o áudio se o texto já foi adicionado.
        # Se twilio_resp.message() já foi chamado, precisamos de um novo.
        # No entanto, o objeto twilio_resp pode ter múltiplos <Message>.
        # Vamos adicionar a mídia à última mensagem criada, se ela não tiver mídia ainda.
        if twilio_resp.children and hasattr(twilio_resp.children[-1], 'media') and not twilio_resp.children[-1].media_url:
            twilio_resp.children[-1].media(audio_url)
        else:
            # Se não há mensagem ou a última já tem mídia, cria uma nova mensagem só para o áudio
            # Isso pode não ser o ideal, pois pode enviar duas notificações ao usuário.
            # Uma abordagem melhor seria construir a mensagem com texto e mídia de uma vez.
            # Mas, dado o fluxo, vamos enviar o áudio como uma mensagem separada se necessário.
            # A melhor forma é enviar uma mensagem com o texto e outra com o áudio.
            # O primeiro twilio_resp.message(bot_reply_text) já enviou o texto.
            # Agora, uma nova mensagem para o áudio.
            audio_message_tag = twilio_resp.message() # Cria uma nova tag <Message>
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

if __name__ == "__main__":
    # Certifique-se de que o BASE_URL está correto, especialmente para ngrok em desenvolvimento
    print(f"Iniciando Flask app. BASE_URL configurado como: {BASE_URL}")
    print(f"Áudios do bot serão servidos de: {app.static_folder}")
    print(f"Para testar o webhook, configure o Twilio para POST em {BASE_URL}/webhook")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "True") == "True")

