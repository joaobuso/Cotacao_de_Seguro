import os
import re
import unicodedata
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("DB_NAME") or "equinos_seguros"

if not MONGO_URI:
    raise Exception("MONGO_URI não configurado no .env")


def get_collection():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db["faq_topics"]


def normalizar_texto(texto: str) -> str:
    texto = (texto or "").lower().strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        char for char in texto
        if unicodedata.category(char) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto


def list_faq_topics(include_inactive: bool = False):
    collection = get_collection()

    filtro = {}
    if not include_inactive:
        filtro["ativo"] = True

    topics = list(collection.find(filtro).sort("ordem", 1))

    for topic in topics:
        topic["_id"] = int(topic["_id"])

    return topics


def get_faq_topics_dict():
    topics = list_faq_topics(include_inactive=False)

    return {
        int(topic["_id"]): {
            "titulo": topic.get("titulo", ""),
            "palavras_chave": topic.get("palavras_chave", []),
            "resumo": topic.get("resumo", "")
        }
        for topic in topics
    }

def get_faq_topic_by_id(topic_id: int) -> dict | None:
    collection = get_collection()

    topic = collection.find_one({
        "_id": int(topic_id),
        "ativo": True
    })

    if not topic:
        return None

    return {
        "titulo": topic.get("titulo", ""),
        "palavras_chave": topic.get("palavras_chave", []),
        "resumo": topic.get("resumo", "")
    }

def get_all_keywords_map():
    keyword_map = {}

    for topic in list_faq_topics(include_inactive=False):
        topic_id = int(topic["_id"])

        for kw in topic.get("palavras_chave", []):
            keyword_map[normalizar_texto(kw)] = topic_id

    return keyword_map


def find_topic_by_message(message: str) -> dict | None:
    """
    Localiza FAQ por palavra-chave.

    Regras:
    - Se a palavra-chave completa estiver na mensagem, pontua alto.
    - Se a mensagem curta estiver dentro da palavra-chave, também pontua.
      Exemplo: mensagem "morte" encontra "morte do cavalo".
    - Se houver interseção relevante de palavras, também pontua.
      Exemplo: mensagem "cólica" encontra "cólica cavalo".
    """

    message_normalized = normalizar_texto(message)

    if not message_normalized:
        return None

    message_tokens = set(message_normalized.split())

    best_match = None
    best_score = 0

    for topic in list_faq_topics(include_inactive=False):
        score = 0

        for kw in topic.get("palavras_chave", []):
            kw_normalized = normalizar_texto(kw)

            if not kw_normalized:
                continue

            kw_tokens = set(kw_normalized.split())

            # Caso ideal: palavra-chave inteira dentro da mensagem.
            if kw_normalized in message_normalized:
                score += 100 + len(kw_tokens)

            # Caso mensagem curta: "morte" dentro de "morte do cavalo".
            elif message_normalized in kw_normalized:
                score += 50 + len(message_tokens)

            # Caso por palavras em comum: "cólica" x "cólica cavalo".
            else:
                intersecao = message_tokens.intersection(kw_tokens)

                if intersecao:
                    score += len(intersecao)

        if score > best_score:
            best_score = score
            best_match = {
                "titulo": topic.get("titulo", ""),
                "palavras_chave": topic.get("palavras_chave", []),
                "resumo": topic.get("resumo", "")
            }

    if best_score >= 1:
        return best_match

    return None


def get_next_topic_id():
    collection = get_collection()
    last = collection.find_one(sort=[("_id", -1)])

    if not last:
        return 1

    return int(last["_id"]) + 1


def create_faq_topic(data: dict, user_email: str = None):
    collection = get_collection()

    topic_id = int(data.get("_id") or get_next_topic_id())

    doc = {
        "_id": topic_id,
        "titulo": data.get("titulo", "").strip(),
        "palavras_chave": data.get("palavras_chave", []),
        "resumo": data.get("resumo", "").strip(),
        "ativo": bool(data.get("ativo", True)),
        "ordem": int(data.get("ordem") or topic_id),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "updated_by": user_email
    }

    collection.insert_one(doc)

    doc["_id"] = int(doc["_id"])
    return doc


def update_faq_topic(topic_id: int, data: dict, user_email: str = None):
    collection = get_collection()

    update_data = {
        "titulo": data.get("titulo", "").strip(),
        "palavras_chave": data.get("palavras_chave", []),
        "resumo": data.get("resumo", "").strip(),
        "ativo": bool(data.get("ativo", True)),
        "ordem": int(data.get("ordem") or topic_id),
        "updated_at": datetime.now(timezone.utc),
        "updated_by": user_email
    }

    collection.update_one(
        {"_id": int(topic_id)},
        {"$set": update_data},
        upsert=False
    )

    return collection.find_one({"_id": int(topic_id)})


def deactivate_faq_topic(topic_id: int, user_email: str = None):
    collection = get_collection()

    collection.update_one(
        {"_id": int(topic_id)},
        {
            "$set": {
                "ativo": False,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": user_email
            }
        }
    )

    return True