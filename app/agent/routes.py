import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from bson import ObjectId

# Importar módulos do projeto
from app.db import database
from app.utils import audio_processor

agent_bp = Blueprint(
    "agent_bp", __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/agent"
)

# Simulação de banco de dados de agentes (em um app real, use um banco de dados)
# Senhas devem ser hasheadas! Exemplo: generate_password_hash("password")
# Carrega lista de agentes definidos no .env
agent_ids = os.getenv("AGENTS", "").split(",")

AGENTS_DB = {}

for agent in agent_ids:
    email = os.getenv(f"AGENT_{agent}_EMAIL")
    name = os.getenv(f"AGENT_{agent}_NAME")
    pwd_hash = os.getenv(f"AGENT_{agent}_PASSWORD_HASH")
    if email and name and pwd_hash:
        AGENTS_DB[email] = {
            "name": name,
            "password_hash": pwd_hash,
            "id": f"agent_{agent}"
        }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "agent_id" not in session:
            flash("Você precisa estar logado para acessar esta página.", "warning")
            return redirect(url_for("agent_bp.login"))
        return f(*args, **kwargs)
    return decorated_function

@agent_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        agent = AGENTS_DB.get(email)

        if agent and check_password_hash(agent["password_hash"], password):
            session["agent_id"] = agent["id"]
            session["agent_name"] = agent["name"]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("agent_bp.dashboard"))
        else:
            flash("Email ou senha inválidos.", "danger")
    return render_template("agent_login.html")

@agent_bp.route("/logout")
@login_required
def logout():
    session.pop("agent_id", None)
    session.pop("agent_name", None)
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("agent_bp.login"))

@agent_bp.route("/dashboard")
@login_required
def dashboard():
    # Buscar conversas que estão aguardando agente ou atribuídas ao agente logado
    conversations_awaiting = database.get_conversations_by_status([database.STATUS_AWAITING_AGENT])
    conversations_active = database.get_conversations_by_status([database.STATUS_AGENT_ACTIVE])
    
    # ADICIONAR: Buscar conversas ativas do bot para monitoramento
    conversations_bot_active = database.get_conversations_by_status([database.STATUS_BOT_ACTIVE])
    
    # ADICIONAR: Buscar todas as conversas recentes (últimas 50)
    try:
        from pymongo import DESCENDING
        all_recent_conversations = list(database.conversations_collection.find().sort("updated_at", DESCENDING).limit(50))
    except:
        all_recent_conversations = []
    
    # Converter ObjectId para string para o template
    for conv in conversations_awaiting:
        conv["_id"] = str(conv["_id"])
    for conv in conversations_active:
        conv["_id"] = str(conv["_id"])
    for conv in conversations_bot_active:
        conv["_id"] = str(conv["_id"])
    for conv in all_recent_conversations:
        conv["_id"] = str(conv["_id"])

    return render_template("agent_dashboard.html", 
                           conversations_awaiting=conversations_awaiting,
                           conversations_active=conversations_active,
                           conversations_bot_active=conversations_bot_active,
                           all_recent_conversations=all_recent_conversations)

@agent_bp.route("/conversation/<conversation_id_str>")
@login_required
def view_conversation(conversation_id_str):
    conversation = database.get_conversation_by_id(conversation_id_str)
    if not conversation:
        flash("Conversa não encontrada.", "danger")
        return redirect(url_for("agent_bp.dashboard"))
    
    # Converter ObjectId para string para o template
    conversation["_id"] = str(conversation["_id"])
    for msg in conversation.get("messages", []):
        msg["message_id"] = str(msg["message_id"])
        
    return render_template("agent_conversation.html", conversation=conversation)

@agent_bp.route("/conversation/<conversation_id_str>/take", methods=["POST"])
@login_required
def take_conversation(conversation_id_str):
    agent_id = session.get("agent_id")
    success = database.set_conversation_status(conversation_id_str, database.STATUS_AGENT_ACTIVE, agent_id=agent_id)
    if success:
        flash("Conversa assumida com sucesso!", "success")
        # Notificar o usuário que um agente assumiu (opcional)
        # twilio_utils.send_whatsapp_message(conversation.phone_number, f"Olá! Sou {session.get('agent_name')}, seu atendente. Como posso ajudar?")
    else:
        flash("Não foi possível assumir a conversa.", "danger")
    return redirect(url_for("agent_bp.view_conversation", conversation_id_str=conversation_id_str))

@agent_bp.route("/conversation/<conversation_id_str>/send", methods=["POST"])
@login_required
def send_agent_message(conversation_id_str):
    agent_id = session.get("agent_id")
    agent_name = session.get("agent_name", "Atendente")
    message_text = request.form.get("message_text")

    if not message_text:
        flash("A mensagem não pode estar vazia.", "warning")
        return redirect(url_for("agent_bp.view_conversation", conversation_id_str=conversation_id_str))

    conversation = database.get_conversation_by_id(conversation_id_str)
    if not conversation:
        flash("Conversa não encontrada.", "danger")
        return redirect(url_for("agent_bp.dashboard"))

    # Salvar mensagem do agente no banco de dados
    database.save_message(conversation["phone_number"], database.SENDER_AGENT, message_text, conversation_id=conversation_id_str)

    # Enviar mensagem para o usuário via Twilio
    try:
        from app.utils import twilio_utils
        success_twilio = twilio_utils.send_whatsapp_message(conversation["phone_number"], message_text)
        if not success_twilio:
            flash("Mensagem salva no histórico, mas falha ao enviar via WhatsApp.", "warning")
        else:
            flash("Mensagem enviada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar mensagem via WhatsApp: {e}", "danger")
        print(f"Erro Twilio: {e}")

    return redirect(url_for("agent_bp.view_conversation", conversation_id_str=conversation_id_str))

@agent_bp.route("/conversation/<conversation_id_str>/resolve", methods=["POST"])
@login_required
def resolve_conversation(conversation_id_str):
    success = database.set_conversation_status(conversation_id_str, database.STATUS_RESOLVED)
    if success:
        flash("Conversa marcada como resolvida!", "success")
        # Notificar o usuário que a conversa foi resolvida (opcional)
        # twilio_utils.send_whatsapp_message(conversation.phone_number, "Sua solicitação foi resolvida. Obrigado por contatar a Equinos Seguros!")
    else:
        flash("Não foi possível resolver a conversa.", "danger")
    return redirect(url_for("agent_bp.dashboard"))

# NOVA ROTA: Para assumir conversas do bot
@agent_bp.route("/conversation/<conversation_id_str>/take_from_bot", methods=["POST"])
@login_required
def take_conversation_from_bot(conversation_id_str):
    agent_id = session.get("agent_id")
    agent_name = session.get("agent_name", "Atendente")
    
    # Mudar status de BOT_ACTIVE para AGENT_ACTIVE
    success = database.set_conversation_status(conversation_id_str, database.STATUS_AGENT_ACTIVE, agent_id=agent_id)
    if success:
        flash(f"Conversa assumida por {agent_name}!", "success")
        
        # Opcional: Enviar mensagem automática informando que um agente assumiu
        try:
            conversation = database.get_conversation_by_id(conversation_id_str)
            if conversation:
                welcome_message = f"Olá! Sou {agent_name}, seu atendente humano. Vou continuar seu atendimento a partir de agora. Como posso ajudar?"
                database.save_message(conversation["phone_number"], database.SENDER_AGENT, welcome_message, conversation_id=conversation_id_str)
                
                # Enviar via WhatsApp
                from app.utils import twilio_utils
                twilio_utils.send_whatsapp_message(conversation["phone_number"], welcome_message)
        except Exception as e:
            print(f"Erro ao enviar mensagem de boas-vindas: {e}")
    else:
        flash("Não foi possível assumir a conversa.", "danger")
    
    return redirect(url_for("agent_bp.view_conversation", conversation_id_str=conversation_id_str))