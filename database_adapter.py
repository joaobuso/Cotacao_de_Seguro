# -*- coding: utf-8 -*-
"""
Adaptador para DatabaseManager
Adiciona métodos necessários para compatibilidade com BotHandler
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DatabaseAdapter:
    """
    Adaptador que adiciona métodos necessários ao DatabaseManager existente
    """
    
    def __init__(self, db_manager):
        """
        Inicializa o adaptador com uma instância do DatabaseManager
        
        Args:
            db_manager: Instância do DatabaseManager original
        """
        self.db_manager = db_manager
    
    def save_message(self, phone: str, sender: str, message: str, 
                     message_type: str = "text", timestamp: datetime = None):
        """
        Salva mensagem no formato esperado pelo BotHandler
        
        Args:
            phone: Número do telefone
            sender: Quem enviou ("user" ou "bot")
            message: Conteúdo da mensagem
            message_type: Tipo da mensagem
            timestamp: Data/hora da mensagem
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Usar o método save_conversation do DatabaseManager original
            if sender == "user":
                # Salvar mensagem do usuário
                self.db_manager.save_conversation(phone, message, "")
            else:
                # Salvar resposta do bot
                # Buscar última mensagem do usuário
                history = self.db_manager.get_conversation_history(phone)
                if history:
                    last_user_msg = history[-1].get('message', '')
                else:
                    last_user_msg = ''
                
                self.db_manager.save_conversation(phone, last_user_msg, message)
            
            logger.info(f"Mensagem salva: {phone} - {sender} - {message[:50]}...")
            
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem: {str(e)}")
    
    def notify_agent_needed(self, phone: str):
        """
        Notifica que um atendente é necessário
        
        Args:
            phone: Número do telefone
        """
        try:
            # Atualizar status do cliente para indicar que precisa de atendente
            client = self.db_manager.get_client_data(phone)
            if client:
                client['status'] = 'awaiting_agent'
                client['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"Atendente solicitado para {phone}")
            
        except Exception as e:
            logger.error(f"Erro ao notificar necessidade de atendente: {str(e)}")
    
    def assign_agent(self, phone: str, agent_id: str):
        """
        Atribui um atendente a uma conversa
        
        Args:
            phone: Número do telefone
            agent_id: ID do atendente
        """
        try:
            client = self.db_manager.get_client_data(phone)
            if client:
                client['status'] = 'agent_active'
                client['agent_id'] = agent_id
                client['agent_assigned_at'] = datetime.now().isoformat()
            
            logger.info(f"Atendente {agent_id} atribuído a {phone}")
            
        except Exception as e:
            logger.error(f"Erro ao atribuir atendente: {str(e)}")
    
    def release_agent(self, phone: str):
        """
        Libera conversa do atendente de volta para o bot
        
        Args:
            phone: Número do telefone
        """
        try:
            client = self.db_manager.get_client_data(phone)
            if client:
                client['status'] = 'collecting'
                if 'agent_id' in client:
                    del client['agent_id']
                if 'agent_assigned_at' in client:
                    del client['agent_assigned_at']
            
            logger.info(f"Conversa {phone} liberada do atendente")
            
        except Exception as e:
            logger.error(f"Erro ao liberar atendente: {str(e)}")
    
    def save_quotation_pdf(self, phone: str, cotacao_id: str, 
                          pdf_path: str, data: Dict):
        """
        Salva PDF de cotação
        
        Args:
            phone: Número do telefone
            cotacao_id: ID da cotação
            pdf_path: Caminho do arquivo PDF
            data: Dados da cotação
        """
        try:
            client = self.db_manager.get_client_data(phone)
            if not client:
                client = {
                    'phone': phone,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'data': {},
                    'status': 'completed',
                    'conversation_count': 0,
                    'quotations': []
                }
                self.db_manager.clients[phone] = client
            
            if 'quotations' not in client:
                client['quotations'] = []
            
            quotation = {
                'cotacao_id': cotacao_id,
                'pdf_path': pdf_path,
                'data': data,
                'created_at': datetime.now().isoformat()
            }
            
            client['quotations'].append(quotation)
            client['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"PDF de cotação salvo: {cotacao_id} para {phone}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar PDF de cotação: {str(e)}")
    
    # Métodos delegados ao DatabaseManager original
    
    def save_client_data(self, phone: str, data: Dict) -> bool:
        """Delega para o DatabaseManager original"""
        return self.db_manager.save_client_data(phone, data)
    
    def get_client_data(self, phone: str) -> Optional[Dict]:
        """Delega para o DatabaseManager original"""
        return self.db_manager.get_client_data(phone)
    
    def get_missing_fields(self, phone: str):
        """Delega para o DatabaseManager original"""
        return self.db_manager.get_missing_fields(phone)
    
    def save_conversation(self, phone: str, message: str, response: str) -> bool:
        """Delega para o DatabaseManager original"""
        return self.db_manager.save_conversation(phone, message, response)
    
    def get_conversation_history(self, phone: str):
        """Delega para o DatabaseManager original"""
        return self.db_manager.get_conversation_history(phone)
    
    def get_all_clients(self) -> Dict:
        """Delega para o DatabaseManager original"""
        return self.db_manager.get_all_clients()
    
    def get_statistics(self) -> Dict:
        """Delega para o DatabaseManager original"""
        return self.db_manager.get_statistics()
    
    def export_client_data(self, phone: str) -> Optional[Dict]:
        """Delega para o DatabaseManager original"""
        return self.db_manager.export_client_data(phone)
    
    def reset_client(self, phone: str):
        """Delega para o DatabaseManager original"""
        return self.db_manager.reset_client(phone)
