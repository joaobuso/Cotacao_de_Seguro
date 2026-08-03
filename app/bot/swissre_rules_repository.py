import os
import copy
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "equinos_seguros")

DEFAULT_SWISSRE_RULES = {
    "_id": "active",
    "general": {
        "cpf": os.getenv("CPF"),
        "brokerId": os.getenv("SUCCPD", "635544270"),
        "productVersionId": "2026_01",
        "codAfinidade": "26",
        "codPlanoPadrao": os.getenv("cod_plano_Padrao", "99999"),
        "codPlanoSimplificado": os.getenv("cod_plano_Simplificado", "00107")
    },
    "limitesPorUtilizacao": {
        "47": {
            "descricao": "Lazer",
            "valorMaximoBasica": float(os.getenv("valor_maximo_lazer", "15000")),
            "aplicarEm": ["basica"]
        }
    },
    "franquiasPorUtilizacaoCobertura": {
        "54|00061": {
            "descricao": "Vaquejada - Básica Vida",
            "pctFranchise": 10
        },
        "54|00450": {
            "descricao": "Vaquejada - Veterinária",
            "pctFranchise": 10
        }
    },
    "products": {
        "64014": {
            "descricao": "Equinos",
            "planos": {
                "99999": {
                    "descricao": "Padrão",
                    "coverages": [
                        {"id": "00061", "descricao": "Básica - Vida", "tipo": "basica", "valorOrigem": "valor_animal"},
                        {"id": "00085", "descricao": "Reembolso de Necropsia", "tipo": "fixa", "valorFixo": 2000},
                        {"id": "11008", "descricao": "Despesas de Salvamento", "tipo": "fixa", "valorFixo": 3000},
                        {"id": "00450", "descricao": "Reembolso de Despesas Veterinárias", "tipo": "veterinaria", "valorMaximo": 30000}
                    ]
                }
            }
        },
        "64017": {
            "descricao": "Asininos e Muares",
            "planos": {
                "99999": {
                    "descricao": "Padrão",
                    "coverages": [
                        {"id": "00003", "descricao": "Básica - Vida", "tipo": "basica", "valorOrigem": "valor_animal"},
                        {"id": "00085", "descricao": "Reembolso de Necropsia", "tipo": "fixa", "valorFixo": 2000},
                        {"id": "11006", "descricao": "Despesas de Salvamento", "tipo": "fixa", "valorFixo": 3000},
                        {"id": "00450", "descricao": "Reembolso de Despesas Veterinárias", "tipo": "veterinaria", "valorMaximo": 30000}
                    ]
                }
            }
        }
    }
}


def get_collection():
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    return db.swissre_rules


def seed_rules_if_needed():
    collection = get_collection()
    existing = collection.find_one({"_id": "active"})

    if not existing:
        rules = copy.deepcopy(DEFAULT_SWISSRE_RULES)
        rules["created_at"] = datetime.utcnow()
        rules["updated_at"] = datetime.utcnow()
        collection.insert_one(rules)

    return True


def get_active_rules():
    collection = get_collection()
    rules = collection.find_one({"_id": "active"})

    if not rules:
        seed_rules_if_needed()
        rules = collection.find_one({"_id": "active"})

    rules.pop("_id", None)
    return rules


def save_active_rules(rules: dict, user_email: str = None):
    collection = get_collection()

    rules_to_save = copy.deepcopy(rules)
    rules_to_save["updated_at"] = datetime.utcnow()
    rules_to_save["updated_by"] = user_email

    collection.update_one(
        {"_id": "active"},
        {"$set": rules_to_save},
        upsert=True
    )

    return True