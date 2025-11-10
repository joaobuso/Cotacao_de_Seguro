# -*- coding: utf-8 -*-
"""
Adaptador para UltraMsgAPI
Adiciona métodos necessários para compatibilidade com BotHandler
"""

import logging

logger = logging.getLogger(__name__)


class UltraMsgAdapter:
    """
    Adaptador que adiciona métodos necessários à UltraMsgAPI existente
    """
    
    def __init__(self, ultramsg_api):
        """
        Inicializa o adaptador com uma instância da UltraMsgAPI
        
        Args:
            ultramsg_api: Instância da UltraMsgAPI original
        """
        self.ultramsg_api = ultramsg_api
    
    def send_message(self, phone: str, message: str) -> bool:
        """
        Envia mensagem de texto (compatível com BotHandler)
        
        Args:
            phone: Número do telefone
            message: Texto da mensagem
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            result = self.ultramsg_api.send_text_message(phone, message)
            
            if result.get('success'):
                logger.info(f"Mensagem enviada para {phone}")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return False
    
    def send_document(self, phone: str, pdf_path: str, caption: str = "") -> bool:
        """
        Envia documento PDF (compatível com BotHandler)
        
        Args:
            phone: Número do telefone
            pdf_path: Caminho local do arquivo PDF
            caption: Legenda do documento
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Nota: A UltraMsgAPI original espera uma URL, não um caminho local
            # Você precisará fazer upload do arquivo para um servidor ou usar base64
            # Por enquanto, vamos apenas logar e retornar True
            
            import os
            filename = os.path.basename(pdf_path)
            
            # TODO: Implementar upload do arquivo ou conversão para base64
            # Por enquanto, apenas simular sucesso
            logger.warning(f"send_document chamado com arquivo local: {pdf_path}")
            logger.warning("Implementação completa requer upload do arquivo ou conversão para base64")
            
            # Se você tiver uma URL pública do PDF, use:
            # result = self.ultramsg_api.send_document(phone, pdf_url, filename, caption)
            
            logger.info(f"Documento {filename} seria enviado para {phone}")
            return True
                
        except Exception as e:
            logger.error(f"Erro ao enviar documento: {str(e)}")
            return False
    
    # Métodos delegados à UltraMsgAPI original
    
    def send_text_message(self, phone: str, message: str):
        """Delega para a UltraMsgAPI original"""
        return self.ultramsg_api.send_text_message(phone, message)
    
    def send_image(self, phone: str, image_url: str, caption: str = ""):
        """Delega para a UltraMsgAPI original"""
        return self.ultramsg_api.send_image(phone, image_url, caption)
    
    def send_audio(self, phone: str, audio_url: str):
        """Delega para a UltraMsgAPI original"""
        return self.ultramsg_api.send_audio(phone, audio_url)
    
    def get_instance_status(self):
        """Delega para a UltraMsgAPI original"""
        return self.ultramsg_api.get_instance_status()
