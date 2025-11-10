# -*- coding: utf-8 -*-
"""
Handler Principal do Bot
Integra o fluxo de conversação com extração de dados e processamento
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

from .conversation_flow import conversation_flow, ConversationState
from .data_extractor import data_extractor

logger = logging.getLogger(__name__)


class BotHandler:
    """
    Handler principal que coordena todo o fluxo do bot
    """
    
    def __init__(self, db_manager=None, ultramsg_api=None, swissre_automation=None):
        """
        Inicializa o handler
        
        Args:
            db_manager: Gerenciador de banco de dados (opcional)
            ultramsg_api: API do UltraMsg para envio de mensagens (opcional)
            swissre_automation: Automação SwissRe para cotações (opcional)
        """
        self.db_manager = db_manager
        self.ultramsg_api = ultramsg_api
        self.swissre_automation = swissre_automation
        
        logger.info("BotHandler inicializado")
    
    def process_message(self, phone: str, message: str, message_type: str = "text") -> Dict:
        """
        Processa mensagem recebida do usuário
        
        Args:
            phone: Número de telefone do usuário
            message: Conteúdo da mensagem
            message_type: Tipo da mensagem (text, audio, image, etc)
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info(f"Processando mensagem de {phone}: {message[:50]}...")
            
            # Salvar mensagem recebida no banco (se disponível)
            if self.db_manager:
                self.db_manager.save_message(
                    phone=phone,
                    sender="user",
                    message=message,
                    message_type=message_type,
                    timestamp=datetime.now()
                )
            
            # Obter estado atual da conversa
            current_state = conversation_flow.get_conversation_state(phone)
            logger.info(f"Estado atual: {current_state.value}")
            
            # Verificar se conversa está com atendente
            if current_state == ConversationState.ATENDENTE_ATIVO:
                logger.info(f"Conversa com atendente ativo, não processar pelo bot")
                return {
                    "status": "agent_active",
                    "message": "Conversa sendo atendida por humano",
                    "should_reply": False
                }
            
            # Processar mensagem baseado no estado
            if current_state in [
                ConversationState.COTACAO_INICIO,
                ConversationState.COTACAO_COLETANDO
            ]:
                # Estados que precisam extrair dados
                return self._process_with_data_extraction(phone, message, current_state)
            
            else:
                # Estados que apenas processam comandos/opções
                return self._process_command(phone, message, current_state)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}", exc_info=True)
            error_response = (
                "😅 Desculpe, ocorreu um erro ao processar sua mensagem.\n\n"
                "Por favor, tente novamente ou digite 'atendente' para falar com um humano."
            )
            self._send_response(phone, error_response)
            return {
                "status": "error",
                "message": str(e),
                "should_reply": True,
                "response": error_response
            }
    
    def _process_with_data_extraction(
        self, 
        phone: str, 
        message: str, 
        current_state: ConversationState
    ) -> Dict:
        """
        Processa mensagem com extração de dados
        """
        # Obter dados existentes
        existing_data = conversation_flow.get_conversation_data(phone)
        
        # Extrair dados da mensagem
        extracted_data = data_extractor.extract_data(message, existing_data)
        
        # Atualizar dados na conversa
        conversation_flow.update_conversation_data(phone, extracted_data)
        
        # Validar dados extraídos
        is_valid, errors = data_extractor.validate_data(extracted_data)
        
        if errors:
            logger.warning(f"Erros de validação: {errors}")
            # Você pode optar por informar os erros ao usuário ou apenas continuar
        
        # Processar input e obter próximo estado
        next_state, response = conversation_flow.process_user_input(phone, message)
        
        # Verificar se precisa processar cotação
        if next_state == ConversationState.COTACAO_PROCESSANDO:
            # Dados completos e confirmados, processar cotação
            return self._process_quotation(phone, extracted_data, response)
        
        # Enviar resposta
        self._send_response(phone, response)
        
        # Salvar resposta no banco
        if self.db_manager:
            self.db_manager.save_message(
                phone=phone,
                sender="bot",
                message=response,
                message_type="text",
                timestamp=datetime.now()
            )
        
        return {
            "status": "success",
            "state": next_state.value,
            "response": response,
            "extracted_data": extracted_data,
            "missing_fields": conversation_flow.get_missing_fields(phone),
            "should_reply": True
        }
    
    def _process_command(self, phone: str, message: str, current_state: ConversationState) -> Dict:
        """
        Processa comandos e opções do menu
        """
        # Processar input e obter próximo estado
        next_state, response = conversation_flow.process_user_input(phone, message)
        
        # Enviar resposta
        self._send_response(phone, response)
        
        # Salvar resposta no banco
        if self.db_manager:
            self.db_manager.save_message(
                phone=phone,
                sender="bot",
                message=response,
                message_type="text",
                timestamp=datetime.now()
            )
        
        # Verificar se mudou para aguardando atendente
        if next_state == ConversationState.AGUARDANDO_ATENDENTE:
            # Notificar sistema de atendentes (se disponível)
            if self.db_manager:
                self.db_manager.notify_agent_needed(phone)
        
        return {
            "status": "success",
            "state": next_state.value,
            "response": response,
            "should_reply": True
        }
    
    def _process_quotation(self, phone: str, data: Dict, initial_response: str) -> Dict:
        """
        Processa a cotação usando automação SwissRe
        """
        try:
            # Enviar mensagem inicial de processamento
            self._send_response(phone, initial_response)
            
            # Salvar mensagem no banco
            if self.db_manager:
                self.db_manager.save_message(
                    phone=phone,
                    sender="bot",
                    message=initial_response,
                    message_type="text",
                    timestamp=datetime.now()
                )
            
            # Executar automação SwissRe (se disponível)
            if self.swissre_automation:
                logger.info(f"Iniciando automação SwissRe para {phone}")
                
                result = self.swissre_automation.process_quotation(data)
                
                if result.get('success'):
                    # Cotação bem-sucedida
                    pdf_path = result.get('pdf_path')
                    cotacao_id = result.get('cotacao_id')
                    
                    # Salvar PDF no banco (se disponível)
                    if self.db_manager and pdf_path:
                        self.db_manager.save_quotation_pdf(
                            phone=phone,
                            cotacao_id=cotacao_id,
                            pdf_path=pdf_path,
                            data=data
                        )
                    
                    # Enviar PDF via WhatsApp
                    if self.ultramsg_api and pdf_path:
                        caption = f"✅ Sua cotação #{cotacao_id} foi gerada com sucesso!"
                        self.ultramsg_api.send_document(phone, pdf_path, caption)
                    
                    # Mensagem de sucesso
                    success_message = (
                        f"✅ *Cotação #{cotacao_id} concluída com sucesso!*\n\n"
                        f"📄 O documento PDF foi enviado acima.\n\n"
                        f"*Deseja mais alguma informação?*\n\n"
                        f"Digite:\n"
                        f"*1* - Fazer nova cotação\n"
                        f"*2* - Falar com atendente\n"
                        f"*3* - Encerrar atendimento"
                    )
                    
                    # Atualizar estado para cotação concluída
                    conversation_flow.set_conversation_state(phone, ConversationState.COTACAO_CONCLUIDA)
                    
                    # Enviar mensagem de sucesso
                    self._send_response(phone, success_message)
                    
                    # Salvar no banco
                    if self.db_manager:
                        self.db_manager.save_message(
                            phone=phone,
                            sender="bot",
                            message=success_message,
                            message_type="text",
                            timestamp=datetime.now()
                        )
                        
                        # Adicionar cotação ao histórico
                        conversation_flow.add_cotacao_realizada(phone, {
                            'cotacao_id': cotacao_id,
                            'data': data,
                            'pdf_path': pdf_path,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    return {
                        "status": "quotation_success",
                        "state": ConversationState.COTACAO_CONCLUIDA.value,
                        "cotacao_id": cotacao_id,
                        "pdf_path": pdf_path,
                        "response": success_message,
                        "should_reply": True
                    }
                
                else:
                    # Erro na cotação
                    error_msg = result.get('error', 'Erro desconhecido')
                    failure_message = (
                        f"❌ *Não foi possível processar sua cotação.*\n\n"
                        f"Motivo: {error_msg}\n\n"
                        f"Por favor, tente novamente ou fale com um atendente.\n\n"
                        f"Digite:\n"
                        f"*1* - Tentar novamente\n"
                        f"*2* - Falar com atendente"
                    )
                    
                    # Voltar para estado de coleta
                    conversation_flow.set_conversation_state(phone, ConversationState.COTACAO_COLETANDO)
                    
                    self._send_response(phone, failure_message)
                    
                    if self.db_manager:
                        self.db_manager.save_message(
                            phone=phone,
                            sender="bot",
                            message=failure_message,
                            message_type="text",
                            timestamp=datetime.now()
                        )
                    
                    return {
                        "status": "quotation_failed",
                        "state": ConversationState.COTACAO_COLETANDO.value,
                        "error": error_msg,
                        "response": failure_message,
                        "should_reply": True
                    }
            
            else:
                # SwissRe não disponível, simular sucesso
                logger.warning("SwissRe automation não disponível, simulando sucesso")
                
                success_message = (
                    f"✅ *Cotação simulada com sucesso!*\n\n"
                    f"📄 Em produção, o PDF seria gerado aqui.\n\n"
                    f"*Deseja mais alguma informação?*\n\n"
                    f"Digite:\n"
                    f"*1* - Fazer nova cotação\n"
                    f"*2* - Falar com atendente\n"
                    f"*3* - Encerrar atendimento"
                )
                
                conversation_flow.set_conversation_state(phone, ConversationState.COTACAO_CONCLUIDA)
                self._send_response(phone, success_message)
                
                return {
                    "status": "quotation_simulated",
                    "state": ConversationState.COTACAO_CONCLUIDA.value,
                    "response": success_message,
                    "should_reply": True
                }
                
        except Exception as e:
            logger.error(f"Erro ao processar cotação: {str(e)}", exc_info=True)
            
            error_message = (
                f"❌ *Erro ao processar cotação*\n\n"
                f"Desculpe, ocorreu um erro inesperado.\n\n"
                f"Um atendente irá entrar em contato com você em breve.\n\n"
                f"Digite 'atendente' para falar com um humano agora."
            )
            
            self._send_response(phone, error_message)
            
            return {
                "status": "quotation_error",
                "error": str(e),
                "response": error_message,
                "should_reply": True
            }
    
    def _send_response(self, phone: str, message: str):
        """
        Envia resposta via UltraMsg
        """
        try:
            if self.ultramsg_api:
                self.ultramsg_api.send_message(phone, message)
                logger.info(f"Resposta enviada para {phone}")
            else:
                logger.warning(f"UltraMsg API não disponível, mensagem não enviada: {message[:50]}")
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {str(e)}")
    
    def handle_agent_takeover(self, phone: str, agent_id: str):
        """
        Marca conversa como assumida por atendente humano
        """
        conversation_flow.set_conversation_state(phone, ConversationState.ATENDENTE_ATIVO)
        
        if self.db_manager:
            self.db_manager.assign_agent(phone, agent_id)
        
        logger.info(f"Conversa {phone} assumida pelo agente {agent_id}")
    
    def handle_agent_release(self, phone: str):
        """
        Libera conversa de volta para o bot
        """
        # Resetar conversa para inicial
        conversation_flow.reset_conversation(phone)
        
        if self.db_manager:
            self.db_manager.release_agent(phone)
        
        # Enviar mensagem de boas-vindas novamente
        welcome_message = (
            "👋 Olá novamente!\n\n"
            "Estou de volta para ajudá-lo.\n\n"
            "Como posso ajudar?\n\n"
            "*1* - Saber sobre a Equinos Seguros\n"
            "*2* - Realizar Cotação de Seguro"
        )
        
        self._send_response(phone, welcome_message)
        
        logger.info(f"Conversa {phone} liberada de volta para o bot")
    
    def get_conversation_status(self, phone: str) -> Dict:
        """
        Retorna status atual da conversa
        """
        state = conversation_flow.get_conversation_state(phone)
        data = conversation_flow.get_conversation_data(phone)
        missing_fields = conversation_flow.get_missing_fields(phone)
        
        return {
            "phone": phone,
            "state": state.value,
            "data": data,
            "missing_fields": missing_fields,
            "is_complete": len(missing_fields) == 0
        }


# Instância global (será inicializada no main.py com dependências)
bot_handler = None
