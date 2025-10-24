# -*- coding: utf-8 -*-
"""
Gerenciador de Banco de Dados para Bot de Cotação de Seguros
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de dados dos clientes (versão simplificada em memória)"""
    
    def __init__(self):
        self.clients = {}
        self.conversations = {}
        
    def save_client_data(self, phone: str, data: Dict) -> bool:
        """Salva dados do cliente"""
        try:
            if phone not in self.clients:
                self.clients[phone] = {
                    'phone': phone,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'data': {},
                    'status': 'collecting',
                    'conversation_count': 0
                }
            
            # Atualizar dados
            self.clients[phone]['data'].update(data)
            self.clients[phone]['updated_at'] = datetime.utcnow().isoformat()
            self.clients[phone]['conversation_count'] += 1
            
            # Verificar se todos os campos obrigatórios foram preenchidos
            required_fields = [
                'nome_animal', 'valor_animal', 'registro', 'raca',
                'data_nascimento', 'sexo', 'utilizacao', 'endereco'
            ]
            
            completed_fields = sum(1 for field in required_fields 
                                 if field in self.clients[phone]['data'] 
                                 and self.clients[phone]['data'][field])
            
            if completed_fields == len(required_fields):
                self.clients[phone]['status'] = 'completed'
            else:
                self.clients[phone]['status'] = 'collecting'
            
            logger.info(f"Dados salvos para {phone}: {completed_fields}/{len(required_fields)} campos")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar dados do cliente {phone}: {str(e)}")
            return False
    
    def get_client_data(self, phone: str) -> Optional[Dict]:
        """Obtém dados do cliente"""
        return self.clients.get(phone)
    
    def get_missing_fields(self, phone: str) -> List[str]:
        """Retorna lista de campos faltantes"""
        required_fields = {
            'nome_animal': 'Nome do Animal',
            'valor_animal': 'Valor do Animal (R$)',
            'registro': 'Número de Registro',
            'raca': 'Raça',
            'data_nascimento': 'Data de Nascimento',
            'sexo': 'Sexo (inteiro, castrado ou fêmea)',
            'utilizacao': 'Utilização (lazer, salto, laço, etc.)',
            'endereco': 'Endereço (CEP e cidade)'
        }
        
        client = self.clients.get(phone, {})
        client_data = client.get('data', {})
        
        missing = []
        for field_key, field_name in required_fields.items():
            if field_key not in client_data or not client_data[field_key]:
                missing.append(field_name)
        
        return missing
    
    def save_conversation(self, phone: str, message: str, response: str) -> bool:
        """Salva conversa"""
        try:
            if phone not in self.conversations:
                self.conversations[phone] = []
            
            conversation_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'message': message,
                'response': response,
                'message_id': len(self.conversations[phone]) + 1
            }
            
            self.conversations[phone].append(conversation_entry)
            logger.info(f"Conversa salva para {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar conversa {phone}: {str(e)}")
            return False
    
    def get_conversation_history(self, phone: str) -> List[Dict]:
        """Obtém histórico de conversas"""
        return self.conversations.get(phone, [])
    
    def get_all_clients(self) -> Dict:
        """Retorna todos os clientes"""
        return self.clients
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas"""
        total_clients = len(self.clients)
        completed_clients = sum(1 for client in self.clients.values() 
                              if client.get('status') == 'completed')
        total_conversations = sum(len(conv) for conv in self.conversations.values())
        
        return {
            'total_clients': total_clients,
            'completed_clients': completed_clients,
            'collecting_clients': total_clients - completed_clients,
            'total_conversations': total_conversations,
            'completion_rate': (completed_clients / total_clients * 100) if total_clients > 0 else 0
        }
    
    def export_client_data(self, phone: str) -> Optional[Dict]:
        """Exporta dados do cliente para processamento"""
        client = self.clients.get(phone)
        if not client or client.get('status') != 'completed':
            return None
        
        return {
            'client_info': {
                'phone': phone,
                'completed_at': client.get('updated_at'),
                'conversation_count': client.get('conversation_count', 0)
            },
            'animal_data': client.get('data', {}),
            'conversation_history': self.get_conversation_history(phone)
        }

# Instância global do gerenciador
db_manager = DatabaseManager()

