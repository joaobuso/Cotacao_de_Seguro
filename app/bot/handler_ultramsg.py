# -*- coding: utf-8 -*-
"""
Handler do bot WhatsApp melhorado para UltraMsg
Mantém todas as funcionalidades do bot de cotação de seguros
"""

import os
import openai
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple

# Importar módulos do projeto
from ultramsg_integration import ultramsg_api, send_whatsapp_message
from app.utils.animal_data_collector import AnimalDataCollector
from app.utils.whatsapp_file_manager import send_pdf_to_whatsapp
from app.bot.swissre import executar_cotacao_swissre
from app.db import database

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Configurar a API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configurar logging
logger = logging.getLogger(__name__)

# Palavras-chave que podem indicar um pedido de handoff
HANDOFF_KEYWORDS = [
    "atendente", "humano", "pessoa", "agente", "falar com alguém", 
    "falar com uma pessoa", "suporte", "ajuda humana", "operador",
    "transferir", "passar para", "quero falar", "preciso falar"
]

class UltraMsgWhatsAppHandler:
    """
    Handler principal para processar mensagens WhatsApp via UltraMsg
    Mantém compatibilidade com funcionalidades existentes
    """
    
    def __init__(self):
        self.ultramsg = ultramsg_api
        
        # Estados da conversa
        self.STATES = {
            "INITIAL": "initial",
            "COLLECTING_DATA": "collecting_data", 
            "DATA_COMPLETE": "data_complete",
            "GENERATING_QUOTE": "generating_quote",
            "QUOTE_SENT": "quote_sent",
            "AWAITING_AGENT": "awaiting_agent",
            "AGENT_ACTIVE": "agent_active"
        }
    
    def process_message(self, phone_number: str, message_body: str, message_type: str = "text", 
                       conversation_id: str = None) -> Tuple[str, bool, Optional[str]]:
        """
        Processa mensagem recebida e retorna resposta
        
        Args:
            phone_number: Número do telefone
            message_body: Conteúdo da mensagem
            message_type: Tipo da mensagem (text, audio, image, etc.)
            conversation_id: ID da conversa (opcional)
            
        Returns:
            Tupla (resposta, is_handoff_request, pdf_path)
        """
        try:
            # Verificar se é um pedido de handoff
            is_handoff_request = self._check_handoff_request(message_body)
            
            if is_handoff_request:
                handoff_message = ("Entendi que você gostaria de falar com um atendente humano. "
                                 "Estou transferindo sua conversa para um de nossos agentes. "
                                 "Por favor, aguarde um momento.")
                return handoff_message, True, None
            
            # Inicializar coletor de dados do animal
            data_collector = AnimalDataCollector(phone_number)
            
            # Extrair e atualizar dados da mensagem
            updated_fields = data_collector.extract_and_update_data(message_body)
            
            # Salvar dados atualizados
            if updated_fields and conversation_id:
                data_collector.save_data(conversation_id)
            
            # Verificar se todos os dados foram coletados
            if data_collector.is_complete():
                # Todos os dados foram coletados, iniciar processo de cotação
                return self._process_complete_quote(data_collector, phone_number)
            
            # Ainda faltam dados, gerar resposta do bot
            return self._generate_data_collection_response(data_collector, message_body, updated_fields)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return ("Desculpe, ocorreu um erro interno. "
                   "Nosso agente entrará em contato com você em breve."), False, None
    
    def _check_handoff_request(self, message: str) -> bool:
        """Verifica se a mensagem contém pedido de handoff"""
        message_lower = message.lower()
        return any(keyword.lower() in message_lower for keyword in HANDOFF_KEYWORDS)
    
    def _generate_data_collection_response(self, data_collector: AnimalDataCollector, 
                                         user_message: str, updated_fields: list) -> Tuple[str, bool, None]:
        """
        Gera resposta para coleta de dados do animal
        """
        try:
            # Preparar contexto para o bot
            dados_coletados = data_collector.get_summary()
            campos_faltantes = data_collector.get_missing_fields()
            
            # Criar prompt personalizado baseado no estado atual
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
            
            # Usar a API da OpenAI para gerar uma resposta
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            # Extrair a resposta do modelo
            bot_response = response.choices[0].message.content.strip()
            
            # Se foram atualizados campos, mencionar isso na resposta
            if updated_fields:
                field_names = [AnimalDataCollector.REQUIRED_FIELDS[field] for field in updated_fields]
                bot_response += f"\n\n✅ Atualizei: {', '.join(field_names)}"
            
            return bot_response, False, None
            
        except Exception as e:
            logger.error(f"Erro ao obter resposta da OpenAI: {str(e)}")
            fallback_response = self._generate_fallback_response(data_collector, updated_fields)
            return fallback_response, False, None
    
    def _generate_fallback_response(self, data_collector: AnimalDataCollector, updated_fields: list) -> str:
        """
        Gera resposta de fallback quando a OpenAI não está disponível
        """
        if not data_collector.data:
            # Primeira interação
            return ("Olá! 👋 Bem-vindo à **Equinos Seguros**!\n\n"
                   "Vou ajudá-lo a fazer uma cotação de seguro para seu animal. "
                   "Para isso, preciso de algumas informações básicas:\n\n"
                   "📋 **Nome do animal, valor, raça, data de nascimento, sexo, utilização e endereço da cocheira.**\n\n"
                   "Pode começar me enviando essas informações?")
        else:
            # Interações subsequentes
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
    
    def _process_complete_quote(self, data_collector: AnimalDataCollector, phone_number: str) -> Tuple[str, bool, Optional[str]]:
        """
        Processa a cotação quando todos os dados estão completos
        """
        try:
            # Obter dados formatados para o SwissRe
            dados_animal = data_collector.get_formatted_data_for_swissre()
            
            # Mostrar resumo final para confirmação
            resumo = data_collector.get_summary()
            resposta_confirmacao = f"""✅ **Perfeito! Coletei todas as informações necessárias.**

{resumo}

🔄 **Iniciando processo de cotação...**

Vou processar sua solicitação no sistema da seguradora. Isso pode levar alguns minutos. 

📄 Assim que a cotação estiver pronta, enviarei o documento PDF com todos os detalhes.

⏳ Por favor, aguarde..."""

            # Executar cotação
            try:
                sucesso, mensagem, pdf_path = executar_cotacao_swissre(dados_animal)
                
                if sucesso and pdf_path:
                    # Tentar enviar PDF via UltraMsg
                    pdf_sent = self._send_pdf_via_ultramsg(phone_number, pdf_path, dados_animal)
                    
                    if pdf_sent:
                        resposta_final = """🎉 **Cotação concluída com sucesso!**

📄 Enviei o documento PDF com sua cotação via WhatsApp.

O arquivo contém:
• Detalhes da cobertura
• Valor do prêmio
• Condições gerais
• Instruções para contratação

💬 Se tiver dúvidas ou desejar prosseguir com a contratação, estou à disposição!

✅ Obrigado por escolher a Equinos Seguros!"""
                    else:
                        resposta_final = """✅ **Cotação processada com sucesso!**

❌ Houve um problema técnico no envio do PDF. 

🔄 **Vou tentar reenviar em alguns instantes.**

💬 Se não receber o documento, entre em contato conosco para que possamos enviar por outro meio.

Obrigado pela paciência!"""
                        
                    return resposta_confirmacao, False, pdf_path if pdf_sent else None
                else:
                    resposta_final = f"""❌ **Problema no processamento da cotação**

Detalhes: {mensagem}

🔄 **Vou tentar novamente em alguns instantes.**

💬 Se o problema persistir, um de nossos atendentes entrará em contato com você.

Pedimos desculpas pelo inconveniente."""
                    
                    return resposta_final, False, None
                    
            except Exception as e:
                logger.error(f"Erro ao executar cotação: {e}")
                resposta_erro = """❌ **Problema técnico no sistema de cotação**

🔧 Nosso sistema está temporariamente indisponível.

👨‍💼 **Um atendente humano entrará em contato com você em breve** para processar sua cotação manualmente.

📞 Ou você pode ligar para nosso atendimento se preferir.

Pedimos desculpas pelo inconveniente."""
                
                return resposta_erro, False, None
                
        except Exception as e:
            logger.error(f"Erro ao processar cotação completa: {e}")
            return ("Ocorreu um erro ao processar sua cotação. "
                   "Um atendente entrará em contato com você em breve."), False, None
    
    def _send_pdf_via_ultramsg(self, phone_number: str, pdf_path: str, dados_animal: dict) -> bool:
        """
        Envia PDF via UltraMsg
        """
        try:
            # Primeiro, precisamos hospedar o PDF em algum lugar acessível
            # Por enquanto, vamos usar a função existente que pode ter lógica de upload
            pdf_url = self._upload_pdf_to_public_url(pdf_path)
            
            if not pdf_url:
                logger.error("Não foi possível obter URL pública para o PDF")
                return False
            
            # Preparar caption
            nome_animal = dados_animal.get('nome_animal', 'Animal')
            caption = f"📄 Cotação de Seguro - {nome_animal}\n\nAqui está sua cotação completa!"
            
            # Enviar documento via UltraMsg
            result = self.ultramsg.send_document(
                phone_number, 
                pdf_url, 
                f"cotacao_{nome_animal.replace(' ', '_')}.pdf",
                caption
            )
            
            if result.get("success"):
                logger.info(f"PDF enviado com sucesso para {phone_number}")
                return True
            else:
                logger.error(f"Erro ao enviar PDF via UltraMsg: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar PDF via UltraMsg: {str(e)}")
            return False
    
    def _upload_pdf_to_public_url(self, pdf_path: str) -> Optional[str]:
        """
        Faz upload do PDF para uma URL pública
        Implementar integração com Cloudinary, AWS S3, ou similar
        """
        try:
            # Por enquanto, usar a função existente do whatsapp_file_manager
            # que pode ter lógica de upload implementada
            from app.utils.whatsapp_file_manager import upload_file_to_public_url
            return upload_file_to_public_url(pdf_path)
        except ImportError:
            # Se não existir, retornar URL local (funciona apenas em desenvolvimento)
            base_url = os.getenv("BASE_URL", "http://localhost:8080")
            filename = os.path.basename(pdf_path)
            return f"{base_url}/static_files/{filename}"
        except Exception as e:
            logger.error(f"Erro ao fazer upload do PDF: {str(e)}")
            return None
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """
        Envia mensagem via UltraMsg
        """
        try:
            result = self.ultramsg.send_text_message(phone_number, message)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return False
    
    def send_document(self, phone_number: str, document_url: str, filename: str, caption: str = "") -> bool:
        """
        Envia documento via UltraMsg
        """
        try:
            result = self.ultramsg.send_document(phone_number, document_url, filename, caption)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Erro ao enviar documento: {str(e)}")
            return False
    
    def send_audio(self, phone_number: str, audio_url: str) -> bool:
        """
        Envia áudio via UltraMsg
        """
        try:
            result = self.ultramsg.send_audio(phone_number, audio_url)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Erro ao enviar áudio: {str(e)}")
            return False

# Função de compatibilidade com código existente
def get_bot_response(user_message: str, phone_number: str, conversation_id: str) -> Tuple[str, bool, Optional[str]]:
    """
    Função de compatibilidade com o código existente
    Mantém a mesma interface da versão Twilio
    """
    handler = UltraMsgWhatsAppHandler()
    return handler.process_message(user_message, phone_number, "text", conversation_id)

# Instância global para uso direto
ultramsg_handler = UltraMsgWhatsAppHandler()

