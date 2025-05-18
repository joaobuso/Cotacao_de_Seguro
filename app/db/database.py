import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Status de conversa
STATUS_BOT_ACTIVE = "BOT_ACTIVE"
STATUS_AWAITING_AGENT = "AWAITING_AGENT"
STATUS_AGENT_ACTIVE = "AGENT_ACTIVE"
STATUS_RESOLVED = "RESOLVED"

# Tipos de remetente
SENDER_USER = "USER"
SENDER_BOT = "BOT"
SENDER_AGENT = "AGENT"

# Configurações do MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "whatsapp_handoff_db")
CONVERSATIONS_COLLECTION = "conversations"

# Conectar ao MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    conversations_collection = db[CONVERSATIONS_COLLECTION]
    print(f"Conexão com MongoDB estabelecida: {MONGO_URI}, DB: {DB_NAME}")
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    # Em um ambiente de produção, você pode querer lidar com isso de forma mais robusta
    # Por exemplo, implementando um fallback para armazenamento local ou reiniciar a aplicação

def get_conversation_status_and_id(phone_number):
    """
    Obtém o status atual da conversa e o ID da conversa para um número de telefone.
    Se não existir uma conversa, retorna STATUS_BOT_ACTIVE e None.
    """
    conversation = conversations_collection.find_one(
        {"phone_number": phone_number},
        sort=[("updated_at", -1)]  # Ordenar por updated_at descendente para pegar a mais recente
    )
    
    if conversation:
        return conversation.get("status", STATUS_BOT_ACTIVE), conversation["_id"]
    else:
        return STATUS_BOT_ACTIVE, None

def get_conversation_by_id(conversation_id_str):
    """
    Obtém uma conversa pelo ID.
    """
    try:
        conversation_id = ObjectId(conversation_id_str)
        return conversations_collection.find_one({"_id": conversation_id})
    except Exception as e:
        print(f"Erro ao buscar conversa por ID: {e}")
        return None

def get_conversations_by_status(status_list):
    """
    Obtém todas as conversas com os status especificados.
    """
    return list(conversations_collection.find(
        {"status": {"$in": status_list}},
        sort=[("updated_at", -1)]  # Ordenar por updated_at descendente
    ))

def set_conversation_status(conversation_id, new_status, agent_id=None):
    """
    Atualiza o status de uma conversa.
    Se agent_id for fornecido, também atualiza o agent_id da conversa.
    """
    try:
        if isinstance(conversation_id, str):
            conversation_id = ObjectId(conversation_id)
        
        update_data = {
            "status": new_status,
            "updated_at": datetime.now()
        }
        
        if agent_id:
            update_data["agent_id"] = agent_id
        
        result = conversations_collection.update_one(
            {"_id": conversation_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"Erro ao atualizar status da conversa: {e}")
        return False

def save_message(phone_number, sender_type, text_content, media_url=None, conversation_id=None):
    """
    Salva uma mensagem no banco de dados.
    Se conversation_id for None, cria uma nova conversa.
    Retorna o ID da conversa.
    """
    try:
        now = datetime.now()
        message = {
            "message_id": ObjectId(),
            "sender_type": sender_type,
            "text_content": text_content,
            "timestamp": now
        }
        
        if media_url:
            message["media_url"] = media_url
        
        if conversation_id:
            # Conversa existente, adicionar mensagem
            if isinstance(conversation_id, str):
                conversation_id = ObjectId(conversation_id)
            
            conversations_collection.update_one(
                {"_id": conversation_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": now}
                }
            )
            return conversation_id
        else:
            # Nova conversa
            new_conversation = {
                "phone_number": phone_number,
                "status": STATUS_BOT_ACTIVE,
                "created_at": now,
                "updated_at": now,
                "messages": [message]
            }
            
            result = conversations_collection.insert_one(new_conversation)
            return result.inserted_id
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}")
        return None
