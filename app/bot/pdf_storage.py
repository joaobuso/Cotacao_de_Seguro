# app/bot/pdf_storage.py
import base64
from pymongo import MongoClient
import os

# Conexão com MongoDB (pega do .env)
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "bot_cotacao")
MONGO_COLLECTION = os.getenv("MONGO_PDF_COLLECTION", "pdfs")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
pdf_collection = db[MONGO_COLLECTION]

def salvar_pdf_mongo(file_path: str, cotacao_id: str) -> str:
    """Converte PDF para base64 e salva no MongoDB."""
    with open(file_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
    result = pdf_collection.insert_one({
        "cotacao_id": cotacao_id,
        "filename": os.path.basename(file_path),
        "pdf_base64": pdf_base64
    })
    return str(result.inserted_id)

def recuperar_pdf_mongo(cotacao_id: str, save_path: str) -> bool:
    """Recupera PDF do banco e salva em arquivo temporário."""
    doc = pdf_collection.find_one({"cotacao_id": cotacao_id})
    if not doc:
        return False
    pdf_bytes = base64.b64decode(doc["pdf_base64"])
    with open(save_path, "wb") as f:
        f.write(pdf_bytes)
    return True
