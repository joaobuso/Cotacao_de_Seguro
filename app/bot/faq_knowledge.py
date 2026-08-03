# -*- coding: utf-8 -*-

"""
Compatibilidade para imports antigos.

A fonte oficial do FAQ agora é o MongoDB,
collection faq_topics, através do faq_repository.py.
"""

from app.bot.faq_repository import (
    normalizar_texto,
    get_all_keywords_map,
    find_topic_by_message,
    get_faq_topics_dict,
    get_faq_topic_by_id,
)

FAQ_TOPICS = {}


def get_faq_topics():
    return get_faq_topics_dict()