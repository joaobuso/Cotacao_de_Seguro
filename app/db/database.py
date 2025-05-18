# /home/ubuntu/whatsapp_handoff_project/app/db/database.py
import os
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path="/home/ubuntu/whatsapp_handoff_project/.env")

# Configuração do MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "whatsapp_handoff_db")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    conversations_collection = db["conversations"]
    print(f"Conectado ao MongoDB: {MONGO_URI}, Banco de Dados: {DB_NAME}")
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    # Em um aplicativo real, você pode querer levantar uma exceção ou ter um fallback
    # Para este exemplo, vamos permitir que continue, mas as operações de DB falharão.
    db = None
    conversations_collection = None

# Status possíveis da conversa
STATUS_BOT_ACTIVE = "BOT_ACTIVE"
STATUS_AWAITING_AGENT = "AWAITING_AGENT"
STATUS_AGENT_ACTIVE = "AGENT_ACTIVE"
STATUS_RESOLVED = "RESOLVED"

# Tipos de remetente
SENDER_USER = "USER"
SENDER_BOT = "BOT"
SENDER_AGENT = "AGENT"

def save_message(phone_number, sender_type, text_content, media_url=None, conversation_id=None):
    """Salva uma mensagem no histórico da conversa e atualiza o timestamp da conversa."""
    if not conversations_collection:
        print("Erro: Coleção de conversas não inicializada.")
        return None

    if not conversation_id:
        # Tenta encontrar uma conversa ativa ou cria uma nova
        conversation = conversations_collection.find_one({
            "phone_number": phone_number,
            "status": {"$ne": STATUS_RESOLVED}
        }, sort=[("updated_at", DESCENDING)])
        
        if conversation:
            conversation_id = conversation["_id"]
        else:
            new_conversation_doc = {
                "phone_number": phone_number,
                "status": STATUS_BOT_ACTIVE,
                "agent_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": []
            }
            try:
                result = conversations_collection.insert_one(new_conversation_doc)
                conversation_id = result.inserted_id
                print(f"Nova conversa criada para {phone_number} com ID: {conversation_id}")
            except Exception as e:
                print(f"Erro ao criar nova conversa: {e}")
                return None
    
    message_doc = {
        "message_id": ObjectId(), # ID único para cada mensagem
        "sender_type": sender_type,
        "text_content": text_content,
        "media_url": media_url,
        "timestamp": datetime.utcnow()
    }
    
    try:
        conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message_doc},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        # print(f"Mensagem salva na conversa {conversation_id} para {phone_number}")
        return str(conversation_id)
    except Exception as e:
        print(f"Erro ao salvar mensagem na conversa {conversation_id}: {e}")
        return None

def get_conversation_status_and_id(phone_number):
    """Obtém o status e o ID da conversa ativa para um número de telefone."""
    if not conversations_collection:
        print("Erro: Coleção de conversas não inicializada.")
        return STATUS_BOT_ACTIVE, None
        
    conversation = conversations_collection.find_one(
        {"phone_number": phone_number, "status": {"$ne": STATUS_RESOLVED}},
        sort=[("updated_at", DESCENDING)]
    )
    if conversation:
        return conversation["status"], str(conversation["_id"])
    return STATUS_BOT_ACTIVE, None

def set_conversation_status(conversation_id, status, agent_id=None):
    """Define o status de uma conversa e, opcionalmente, o ID do agente."""
    if not conversations_collection:
        print("Erro: Coleção de conversas não inicializada.")
        return False
        
    update_fields = {"status": status, "updated_at": datetime.utcnow()}
    if agent_id:
        update_fields["agent_id"] = agent_id
    
    try:
        result = conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": update_fields}
        )
        if result.modified_count > 0:
            print(f"Status da conversa {conversation_id} atualizado para {status}")
            return True
        # print(f"Nenhuma conversa encontrada ou status já era {status} para {conversation_id}")
        return False # Pode ser que não encontrou ou o status já era o mesmo
    except Exception as e:
        print(f"Erro ao atualizar status da conversa {conversation_id}: {e}")
        return False

def get_conversation_by_id(conversation_id):
    """Retorna uma conversa específica pelo seu ID."""
    if not conversations_collection:
        print("Erro: Coleção de conversas não inicializada.")
        return None
    try:
        return conversations_collection.find_one({"_id": ObjectId(conversation_id)})
    except Exception as e:
        print(f"Erro ao buscar conversa por ID {conversation_id}: {e}")
        return None

def get_conversations_by_status(status_list, limit=50):
    """Retorna conversas que correspondem a uma lista de status."""
    if not conversations_collection:
        print("Erro: Coleção de conversas não inicializada.")
        return []
    try:
        return list(conversations_collection.find({"status": {"$in": status_list}}).sort("updated_at", DESCENDING).limit(limit))
    except Exception as e:
        print(f"Erro ao buscar conversas por status {status_list}: {e}")
        return []

# Exemplo de como usar (pode ser removido ou comentado)
if __name__ == "__main__":
    if conversations_collection is not None:
        print("Testando módulo database.py...")
        test_phone = "whatsapp:+12345678900"
        
        # Limpar conversas de teste anteriores
        # conversations_collection.delete_many({"phone_number": test_phone})

        # Teste 1: Salvar primeira mensagem (cria conversa)
        conv_id = save_message(test_phone, SENDER_USER, "Olá, preciso de ajuda!")
        print(f"ID da Conversa: {conv_id}")

        # Teste 2: Obter status
        status, c_id = get_conversation_status_and_id(test_phone)
        print(f"Status: {status}, ID da Conversa (get): {c_id}")
        assert c_id == conv_id
        assert status == STATUS_BOT_ACTIVE

        # Teste 3: Salvar segunda mensagem na mesma conversa
        save_message(test_phone, SENDER_BOT, "Claro, como posso ajudar?", conversation_id=conv_id)

        # Teste 4: Mudar status para AWAITING_AGENT
        set_conversation_status(conv_id, STATUS_AWAITING_AGENT)
        status, _ = get_conversation_status_and_id(test_phone)
        print(f"Novo Status: {status}")
        assert status == STATUS_AWAITING_AGENT

        # Teste 5: Mudar status para AGENT_ACTIVE com agent_id
        set_conversation_status(conv_id, STATUS_AGENT_ACTIVE, agent_id="agent_007")
        status, _ = get_conversation_status_and_id(test_phone)
        print(f"Novo Status: {status}")
        assert status == STATUS_AGENT_ACTIVE

        # Teste 6: Obter conversa por ID
        conversation_doc = get_conversation_by_id(conv_id)
        if conversation_doc:
            print(f"Conversa obtida por ID: {len(conversation_doc.get('messages', []))} mensagens")
            assert len(conversation_doc.get('messages', [])) == 2
            assert conversation_doc.get('agent_id') == "agent_007"

        # Teste 7: Listar conversas aguardando agente
        awaiting_convs = get_conversations_by_status([STATUS_AWAITING_AGENT, STATUS_AGENT_ACTIVE])
        print(f"Conversas aguardando/com agente: {len(awaiting_convs)}")
        # O status foi mudado para AGENT_ACTIVE, então não deve estar em AWAITING_AGENT
        # Mas deve estar em AGENT_ACTIVE
        found_in_list = any(str(c['_id']) == conv_id for c in awaiting_convs)
        assert found_in_list

        # Teste 8: Resolver conversa
        set_conversation_status(conv_id, STATUS_RESOLVED)
        status, _ = get_conversation_status_and_id(test_phone)
        print(f"Status após resolver: {status}") # Deve ser BOT_ACTIVE para uma nova conversa
        assert status == STATUS_BOT_ACTIVE # Pois get_conversation_status busca uma NÃO resolvida

        # Verificar que a conversa resolvida ainda existe mas não é "ativa"
        resolved_conv = get_conversation_by_id(conv_id)
        assert resolved_conv['status'] == STATUS_RESOLVED

        print("Testes do database.py concluídos.")
    else:
        print("Não foi possível executar os testes do database.py devido a erro na conexão com o MongoDB.")

