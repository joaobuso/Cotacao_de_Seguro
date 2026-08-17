# -*- coding: utf-8 -*-

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("DB_NAME") or "equinos_seguros"

DEFAULT_SCHEDULE = {
    "_id": "active",
    "enabled": True,
    "timezone": "America/Sao_Paulo",
    "sendAutoMessageWhenInactive": False,
    "inactiveMessage": (
        "No momento, seu atendimento será realizado por um analista humano. "
        "Aguarde um instante, por favor."
    ),
    "slots": [
        {
            "id": "noite",
            "descricao": "Atuação noturna",
            "active": True,
            "days": [0, 1, 2, 3, 4, 5, 6],
            "start": "18:00",
            "end": "09:00"
        },
        {
            "id": "almoco",
            "descricao": "Atuação horário de almoço",
            "active": True,
            "days": [0, 1, 2, 3, 4, 5, 6],
            "start": "12:00",
            "end": "14:00"
        }
    ]
}


def get_collection():
    if not MONGO_URI:
        raise Exception("MONGO_URI não configurado no .env")

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db["bot_work_schedule"]


def seed_bot_schedule_if_needed():
    collection = get_collection()
    existing = collection.find_one({"_id": "active"})

    if not existing:
        collection.insert_one(DEFAULT_SCHEDULE.copy())

    return True


def get_bot_schedule():
    collection = get_collection()
    schedule = collection.find_one({"_id": "active"})

    if not schedule:
        seed_bot_schedule_if_needed()
        schedule = collection.find_one({"_id": "active"})

    schedule["_id"] = str(schedule["_id"])
    return schedule


def save_bot_schedule(data: dict, user_email: str = None):
    collection = get_collection()

    data_to_save = {
        "enabled": bool(data.get("enabled", True)),
        "timezone": data.get("timezone", "America/Sao_Paulo"),
        "sendAutoMessageWhenInactive": bool(data.get("sendAutoMessageWhenInactive", False)),
        "inactiveMessage": data.get("inactiveMessage", ""),
        "slots": data.get("slots", []),
        "updated_at": datetime.utcnow(),
        "updated_by": user_email
    }

    collection.update_one(
        {"_id": "active"},
        {"$set": data_to_save},
        upsert=True
    )

    return True


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def is_slot_active_now(slot: dict, now_local: datetime) -> bool:
    if not slot.get("active", True):
        return False

    start = parse_hhmm(slot["start"])
    end = parse_hhmm(slot["end"])

    today = now_local.weekday()
    previous_day = (today - 1) % 7
    current_time = now_local.time()

    days = slot.get("days", [])

    # Caso normal: 12:00 até 14:00
    if start < end:
        return today in days and start <= current_time < end

    # Caso cruza meia-noite: 18:00 até 09:00
    if start > end:
        active_today_after_start = today in days and current_time >= start
        active_previous_day_before_end = previous_day in days and current_time < end

        return active_today_after_start or active_previous_day_before_end

    # start == end: considera desativado para evitar 24h acidental
    return False


def is_bot_active_now() -> tuple[bool, dict]:
    schedule = get_bot_schedule()

    if not schedule.get("enabled", True):
        return False, {
            "reason": "schedule_disabled",
            "schedule": schedule
        }

    timezone_name = schedule.get("timezone", "America/Sao_Paulo")
    now_local = datetime.now(ZoneInfo(timezone_name))

    for slot in schedule.get("slots", []):
        if is_slot_active_now(slot, now_local):
            return True, {
                "reason": "inside_bot_working_hours",
                "slot": slot,
                "now": now_local.isoformat(),
                "schedule": schedule
            }

    return False, {
        "reason": "outside_bot_working_hours",
        "now": now_local.isoformat(),
        "schedule": schedule
    }