# -*- coding: utf-8 -*-
"""
Handler principal para processar mensagens do WhatsApp
"""

import os
import openai
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.integrations.ultramsg_api import ultramsg_api
from app.bot.animal_data_collector import AnimalDataCollector
from app.bot.swissre_automation import SwissReAutomation
from app.db.database import Database
from app.utils.audio_processor import AudioProcessor
from app.utils.file_manager import FileManager

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

class MessageHandler:
    """
    Handler principal para processar mensagens do WhatsApp
    """
    
    def __init__(self):
        self.database = Database()
        self.audio_processor = AudioProcessor()
        self.file_manager = FileManager()
        self.swissre = SwissReAutomation()
        
        # Palavras-chave para handoff
        self.handoff_keywords = [
            "atendente", "humano", "pessoa", "agente", "falar com alguém", 
            "falar com uma pessoa", "suporte", "ajuda humana", "operador",
            "transferir", "passar para", "quero falar", "preciso falar"
        ]
    
    def process_message(self, phone_number: str, message_body: str, 
                       message_type: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem recebida
        
        Args:
            phone_number: Número do telefone
            message_body: Conteúdo da mensagem
            message_type: Tipo da mensagem (text, audio, image, etc.)
            message_data: Dados completos da mensagem
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            # Salvar mensagem recebida
            conversation_id = self.database.save_message(
                phone_number, "user", message_body, message_type, message_data
            )
            
            # Processar áudio se necessário
            if message_type == "audio":
                audio_url = message_data.get("media_url")
                if audio_url:
                    transcribed_text = self.audio_processor.transcribe_audio(audio_url)
                    if transcribed_text:
                        message_body = transcribed_text
                        logger.info(f"Áudio transcrito: {transcribed_text}")
                    else:
                        error_msg = "Desculpe, não consegui entender seu áudio. Por favor, tente novamente ou envie uma mensagem de texto."
                        self._send_response(phone_number, error_msg, conversation_id)
                        return {"status": "audio_error", "message": error_msg}
            
            # Verificar se é pedido de handoff
            if self._is_handoff_request(message_body):
                handoff_msg = ("Entendi que você gostaria de falar com um atendente humano. "
                             "Estou transferindo sua conversa para um de nossos agentes. "
                             "Por favor, aguarde um momento.")
                
                self._send_response(phone_number, handoff_msg, conversation_id)
                self.database.set_conversation_status(conversation_id, "awaiting_agent")
                
                return {"status": "handoff_requested", "message": handoff_msg}
            
            # Verificar status da conversa
            conversation_status = self.database.get_conversation_status(conversation_id)
            
            if conversation_status in ["awaiting_agent", "agent_active"]:
                logger.info(f"Mensagem para agente: {phone_number}")
                return {"status": "forwarded_to_agent", "conversation_id": conversation_id}
            
            # Processar com o bot
            return self._process_bot_conversation(phone_number, message_body, conversation_id)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            error_msg = "Desculpe, ocorreu um erro interno. Nosso agente entrará em contato com você em breve."
            self._send_response(phone_number, error_msg, None)
            return {"status": "error", "message": str(e)}
    
    def _process_bot_conversation(self, phone_number: str, message_body: str, 
                                 conversation_id: str) -> Dict[str, Any]:
        """
        Processa conversa com o bot
        """
        try:
            # Inicializar coletor de dados
            data_collector = AnimalDataCollector(phone_number)
            
            # Extrair e atualizar dados da mensagem
            updated_fields = data_collector.extract_and_update_data(message_body)
            
            # Salvar dados atualizados
            if updated_fields:
                data_collector.save_data(conversation_id)
            
            # Verificar se todos os dados foram coletados
            if data_collector.is_complete():
                return self._process_complete_quote(data_collector, phone_number, conversation_id)
            
            # Gerar resposta para coleta de dados
            bot_response = self._generate_data_collection_response(data_collector, message_body, updated_fields)
            
            # Enviar resposta
            self._send_response(phone_number, bot_response, conversation_id)
            
            return {
                "status": "data_collection",
                "message": bot_response,
                "updated_fields": updated_fields,
                "missing_fields": data_collector.get_missing_fields()
            }
            
        except Exception as e:
            logger.error(f"Erro na conversa do bot: {str(e)}")
            error_msg = "Desculpe, ocorreu um erro. Vou transferir você para um atendente."
            self._send_response(phone_number, error_msg, conversation_id)
            return {"status": "error", "message": str(e)}
    
    def _generate_data_collection_response(self, data_collector: AnimalDataCollector, 
                                         user_message: str, updated_fields: list) -> str:
        """
        Gera resposta para coleta de dados usando OpenAI
        """
        try:
            dados_coletados = data_collector.get_summary()
            campos_faltantes = data_collector.get_missing_fields()
            
            if not data_collector.data:
                # Primeira interação
                system_prompt = """
                Você é um assistente de seguros para equinos da empresa **Equinos Seguros**, especializado em cotação de seguros Pecuário Individual, Rebanhos ou animais de Competição e Exposição.

                Esta é a primeira interação com o cliente. Apresente-se de forma calorosa e explique que você irá coletar as informações necessárias para realizar a cotação do seguro.

                Explique que precisa das seguintes informações obrigatórias:
                - Nome do Animal
                - Valor do Animal
                - Número de Registro ou Passaporte (se tiver)
                - Raça
                - Data de Nascimento
                - Sexo (inteiro, castrado ou fêmea)
                - Utilização (lazer, salto, laço etc.)
                - Endereço da Cocheira (CEP e cidade)

                Peça para o cliente começar fornecendo essas informações. Seja acolhedor e profissional.
                Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas.
                """
            else:
                # Interações subsequentes
                system_prompt = f"""
                Você é um assistente de seguros para equinos da empresa **Equinos Seguros**.

                DADOS JÁ COLETADOS:
                {dados_coletados}

                CAMPOS AINDA FALTANTES:
                {', '.join(campos_faltantes) if campos_faltantes else 'Nenhum'}

                Sua tarefa é:
                1. Agradecer pelas informações fornecidas
                2. Se ainda faltam campos, perguntar especificamente pelos campos faltantes
                3. Ser educado e encorajador
                4. Manter o foco na coleta de dados

                Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas.
                """
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            bot_response = response.choices[0].message.content.strip()
            
            # Adicionar campos atualizados se houver
            if updated_fields:
                field_names = [AnimalDataCollector.REQUIRED_FIELDS[field] for field in updated_fields]
                bot_response += f"\n\n✅ Atualizei: {', '.join(field_names)}"
            
            return bot_response
            
        except Exception as e:
            logger.error(f"Erro ao obter resposta da OpenAI: {str(e)}")
            return self._generate_fallback_response(data_collector, updated_fields)
    
    def _generate_fallback_response(self, data_collector: AnimalDataCollector, updated_fields: list) -> str:
        """
        Gera resposta de fallback quando OpenAI não está disponível
        """
        if not data_collector.data:
            return ("Olá! 👋 Bem-vindo à **Equinos Seguros**!\n\n"
                   "Vou ajudá-lo a fazer uma cotação de seguro para seu animal. "
                   "Para isso, preciso de algumas informações básicas:\n\n"
                   "📋 **Nome do animal, valor, raça, data de nascimento, sexo, utilização e endereço da cocheira.**\n\n"
                   "Pode começar me enviando essas informações?")
        else:
            campos_faltantes = data_collector.get_missing_fields()
            
            if campos_faltantes:
                field_names = [AnimalDataCollector.REQUIRED_FIELDS[field] for field in campos_faltantes]
                response = f"Obrigado pelas informações! 📝\n\nAinda preciso de:\n• {chr(10).join(['• ' + name for name in field_names])}"
                
                if updated_fields:
                    updated_names = [AnimalDataCollector.REQUIRED_FIELDS[field] for field in updated_fields]
                    response += f"\n\n✅ Atualizei: {', '.join(updated_names)}"
                
                return response
            else:
                return "Perfeito! Tenho todas as informações necessárias. Vou processar sua cotação agora!"
    
    def _process_complete_quote(self, data_collector: AnimalDataCollector, 
                               phone_number: str, conversation_id: str) -> Dict[str, Any]:
        """
        Processa cotação quando todos os dados estão completos
        """
        try:
            # Mostrar resumo
            resumo = data_collector.get_summary()
            confirmacao_msg = f"""✅ **Perfeito! Coletei todas as informações necessárias.**

{resumo}

🔄 **Iniciando processo de cotação...**

Vou processar sua solicitação no sistema da seguradora. Isso pode levar alguns minutos.

📄 Assim que a cotação estiver pronta, enviarei o documento PDF com todos os detalhes.

⏳ Por favor, aguarde..."""
            
            self._send_response(phone_number, confirmacao_msg, conversation_id)
            
            # Executar automação SwissRe
            dados_animal = data_collector.get_formatted_data_for_swissre()
            sucesso, mensagem, pdf_path = self.swissre.executar_cotacao(dados_animal)
            
            if sucesso and pdf_path:
                # Enviar PDF
                pdf_sent = self.file_manager.send_pdf_to_whatsapp(phone_number, pdf_path, dados_animal)
                
                if pdf_sent:
                    final_msg = """🎉 **Cotação concluída com sucesso!**

📄 Enviei o documento PDF com sua cotação via WhatsApp.

O arquivo contém:
• Detalhes da cobertura
• Valor do prêmio
• Condições gerais
• Instruções para contratação

💬 Se tiver dúvidas ou desejar prosseguir com a contratação, estou à disposição!

✅ Obrigado por escolher a Equinos Seguros!"""
                else:
                    final_msg = """✅ **Cotação processada com sucesso!**

❌ Houve um problema técnico no envio do PDF.

🔄 **Vou tentar reenviar em alguns instantes.**

💬 Se não receber o documento, entre em contato conosco."""
                
                self._send_response(phone_number, final_msg, conversation_id)
                
                return {
                    "status": "quote_completed",
                    "message": final_msg,
                    "pdf_sent": pdf_sent,
                    "pdf_path": pdf_path
                }
            else:
                error_msg = f"""❌ **Problema no processamento da cotação**

Detalhes: {mensagem}

🔄 **Vou tentar novamente em alguns instantes.**

💬 Se o problema persistir, um de nossos atendentes entrará em contato com você."""
                
                self._send_response(phone_number, error_msg, conversation_id)
                
                return {"status": "quote_error", "message": error_msg}
                
        except Exception as e:
            logger.error(f"Erro ao processar cotação completa: {str(e)}")
            error_msg = """❌ **Problema técnico no sistema de cotação**

🔧 Nosso sistema está temporariamente indisponível.

👨‍💼 **Um atendente humano entrará em contato com você em breve** para processar sua cotação manualmente."""
            
            self._send_response(phone_number, error_msg, conversation_id)
            return {"status": "system_error", "message": str(e)}
    
    def _send_response(self, phone_number: str, message: str, conversation_id: Optional[str]):
        """
        Envia resposta via UltraMsg e salva no banco
        """
        try:
            # Enviar via UltraMsg
            result = ultramsg_api.send_text_message(phone_number, message)
            
            if result.get("success"):
                logger.info(f"Resposta enviada para {phone_number}")
                
                # Salvar no banco
                if conversation_id:
                    self.database.save_message(conversation_id, "bot", message, "text", {})
            else:
                logger.error(f"Erro ao enviar resposta: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {str(e)}")
    
    def _is_handoff_request(self, message: str) -> bool:
        """
        Verifica se a mensagem contém pedido de handoff
        """
        message_lower = message.lower()
        return any(keyword.lower() in message_lower for keyword in self.handoff_keywords)

