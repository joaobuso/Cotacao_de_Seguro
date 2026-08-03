import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

from faq_knowledge import FAQ_TOPICS

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("DB_NAME") or "equinos_seguros"

if not MONGO_URI:
    raise Exception("MONGO_URI não configurado no .env")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db["faq_topics"]

operations = []

for topic_id, topic in FAQ_TOPICS.items():
    operations.append(
        UpdateOne(
            {"_id": int(topic_id)},
            {
                "$set": {
                    "titulo": topic.get("titulo", ""),
                    "palavras_chave": topic.get("palavras_chave", []),
                    "resumo": topic.get("resumo", ""),
                    "ativo": True,
                    "ordem": int(topic_id),
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": "script_migrar_faq_topics_para_mongo"
                },
                "$setOnInsert": {
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
    )

if operations:
    result = collection.bulk_write(operations)
    print("FAQ migrado com sucesso.")
    print("upserted_count:", result.upserted_count)
    print("modified_count:", result.modified_count)
else:
    print("Nenhum tópico encontrado para migrar.")