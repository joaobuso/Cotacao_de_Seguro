# -*- coding: utf-8 -*-
"""
Módulo de banco de dados MongoDB
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class Database:
    """
    Classe para gerenciar operações do banco de dados
    """
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        self.client = None
        self.db = None
        
        if self.mongo_uri:
            self._connect()
        else:
            logger.warning("MONGO_URI não configurado - usando dados em memória")
            self._use_memory_storage()
    
    def _connect(self):
        """
        Conecta ao MongoDB
        """
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client.get_default_database()
            
            # Testar conexão
            self.client.admin.command('ping')
            logger.info("✅ Conectado ao MongoDB")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar MongoDB: {str(e)}")
            self._use_memory_storage()
    
    def _use_memory_storage(self):
        """
        Usa armazenamento em memória como fallback
        """
        self.memory_storage = {
            'conversations': {},
            'messages': {},
            'animal_data': {}
        }
        logger.info("📝 Usando armazenamento em memória")
    
    def check_connection(self) -> bool:
        """
        Verifica se a conexão está ativa
        """
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
            return False
        except:
            return False
    
    def save_message(self, phone_number: str, sender: str, message: str, 
                    message_type: str = "text", metadata: Dict[str, Any] = None) -> str:
        """
        Salva mensagem no banco de dados
        
        Args:
            phone_number: Número do telefone
            sender: Remetente (user/bot)
            message: Conteúdo da mensagem
            message_type: Tipo da mensagem
            metadata: Metadados adicionais
            
        Returns:
            ID da conversa
        """
        try:
            # Obter ou criar conversa
            conversation_id = self._get_or_create_conversation(phone_number)
            
            message_data = {
                'conversation_id': conversation_id,
                'phone_number': phone_number,
                'sender': sender,
                'message': message,
                'message_type': message_type,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow()
            }
            
            if self.db:
                # Salvar no MongoDB
                result = self.db.messages.insert_one(message_data)
                logger.info(f"Mensagem salva no MongoDB: {result.inserted_id}")
            else:
                # Salvar em memória
                message_id = str(len(self.memory_storage['messages']))
                self.memory_storage['messages'][message_id] = message_data
                logger.info(f"Mensagem salva em memória: {message_id}")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem: {str(e)}")
            return None
    
    def _get_or_create_conversation(self, phone_number: str) -> str:
        """
        Obtém conversa existente ou cria nova
        """
        try:
            if self.db:
                # Buscar conversa existente
                conversation = self.db.conversations.find_one({
                    'phone_number': phone_number,
                    'status': {'$in': ['active', 'bot_active', 'awaiting_agent', 'agent_active']}
                })
                
                if conversation:
                    return str(conversation['_id'])
                
                # Criar nova conversa
                conversation_data = {
                    'phone_number': phone_number,
                    'status': 'bot_active',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                result = self.db.conversations.insert_one(conversation_data)
                return str(result.inserted_id)
            
            else:
                # Usar memória
                for conv_id, conv_data in self.memory_storage['conversations'].items():
                    if conv_data['phone_number'] == phone_number:
                        return conv_id
                
                # Criar nova
                conv_id = str(len(self.memory_storage['conversations']))
                self.memory_storage['conversations'][conv_id] = {
                    'phone_number': phone_number,
                    'status': 'bot_active',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                return conv_id
                
        except Exception as e:
            logger.error(f"Erro ao obter/criar conversa: {str(e)}")
            return str(datetime.utcnow().timestamp())
    
    def get_conversation_status(self, conversation_id: str) -> str:
        """
        Obtém status da conversa
        """
        try:
            if self.db:
                conversation = self.db.conversations.find_one({'_id': ObjectId(conversation_id)})
                if conversation:
                    return conversation.get('status', 'bot_active')
            else:
                conversation = self.memory_storage['conversations'].get(conversation_id)
                if conversation:
                    return conversation.get('status', 'bot_active')
            
            return 'bot_active'
            
        except Exception as e:
            logger.error(f"Erro ao obter status da conversa: {str(e)}")
            return 'bot_active'
    
    def set_conversation_status(self, conversation_id: str, status: str):
        """
        Define status da conversa
        """
        try:
            if self.db:
                self.db.conversations.update_one(
                    {'_id': ObjectId(conversation_id)},
                    {
                        '$set': {
                            'status': status,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
            else:
                if conversation_id in self.memory_storage['conversations']:
                    self.memory_storage['conversations'][conversation_id]['status'] = status
                    self.memory_storage['conversations'][conversation_id]['updated_at'] = datetime.utcnow()
            
            logger.info(f"Status da conversa {conversation_id} alterado para {status}")
            
        except Exception as e:
            logger.error(f"Erro ao definir status da conversa: {str(e)}")
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtém mensagens da conversa
        """
        try:
            if self.db:
                messages = list(self.db.messages.find(
                    {'conversation_id': conversation_id}
                ).sort('timestamp', -1).limit(limit))
                
                # Converter ObjectId para string
                for msg in messages:
                    msg['_id'] = str(msg['_id'])
                
                return messages
            else:
                messages = []
                for msg_data in self.memory_storage['messages'].values():
                    if msg_data['conversation_id'] == conversation_id:
                        messages.append(msg_data)
                
                # Ordenar por timestamp
                messages.sort(key=lambda x: x['timestamp'], reverse=True)
                return messages[:limit]
                
        except Exception as e:
            logger.error(f"Erro ao obter mensagens: {str(e)}")
            return []
    
    def save_animal_data(self, conversation_id: str, animal_data: Dict[str, Any]):
        """
        Salva dados do animal
        """
        try:
            data = {
                'conversation_id': conversation_id,
                'animal_data': animal_data,
                'timestamp': datetime.utcnow()
            }
            
            if self.db:
                # Atualizar ou inserir
                self.db.animal_data.update_one(
                    {'conversation_id': conversation_id},
                    {'$set': data},
                    upsert=True
                )
            else:
                self.memory_storage['animal_data'][conversation_id] = data
            
            logger.info(f"Dados do animal salvos para conversa {conversation_id}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar dados do animal: {str(e)}")
    
    def get_animal_data(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados do animal
        """
        try:
            if self.db:
                data = self.db.animal_data.find_one({'conversation_id': conversation_id})
                if data:
                    return data.get('animal_data')
            else:
                data = self.memory_storage['animal_data'].get(conversation_id)
                if data:
                    return data.get('animal_data')
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter dados do animal: {str(e)}")
            return None
    
    def get_active_conversations(self) -> List[Dict[str, Any]]:
        """
        Obtém conversas ativas
        """
        try:
            if self.db:
                conversations = list(self.db.conversations.find({
                    'status': {'$in': ['bot_active', 'awaiting_agent', 'agent_active']}
                }).sort('updated_at', -1))
                
                # Converter ObjectId para string
                for conv in conversations:
                    conv['_id'] = str(conv['_id'])
                
                return conversations
            else:
                conversations = []
                for conv_id, conv_data in self.memory_storage['conversations'].items():
                    if conv_data['status'] in ['bot_active', 'awaiting_agent', 'agent_active']:
                        conv_data['_id'] = conv_id
                        conversations.append(conv_data)
                
                # Ordenar por updated_at
                conversations.sort(key=lambda x: x['updated_at'], reverse=True)
                return conversations
                
        except Exception as e:
            logger.error(f"Erro ao obter conversas ativas: {str(e)}")
            return []
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas das conversas
        """
        try:
            if self.db:
                total_conversations = self.db.conversations.count_documents({})
                active_conversations = self.db.conversations.count_documents({
                    'status': {'$in': ['bot_active', 'awaiting_agent', 'agent_active']}
                })
                total_messages = self.db.messages.count_documents({})
                
                return {
                    'total_conversations': total_conversations,
                    'active_conversations': active_conversations,
                    'total_messages': total_messages
                }
            else:
                total_conversations = len(self.memory_storage['conversations'])
                active_conversations = sum(1 for conv in self.memory_storage['conversations'].values() 
                                         if conv['status'] in ['bot_active', 'awaiting_agent', 'agent_active'])
                total_messages = len(self.memory_storage['messages'])
                
                return {
                    'total_conversations': total_conversations,
                    'active_conversations': active_conversations,
                    'total_messages': total_messages
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                'total_conversations': 0,
                'active_conversations': 0,
                'total_messages': 0
            }

