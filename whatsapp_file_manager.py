# -*- coding: utf-8 -*-
"""
Gerenciador de arquivos WhatsApp para UltraMsg
Substitui funcionalidades do Twilio para envio de arquivos
"""

import os
import logging
import requests
import cloudinary
import cloudinary.uploader
from typing import Optional, Dict, Any
from ultramsg_integration import ultramsg_api

# Configurar logging
logger = logging.getLogger(__name__)

# Configurar Cloudinary (se disponível)
try:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )
    CLOUDINARY_AVAILABLE = True
except:
    CLOUDINARY_AVAILABLE = False
    logger.warning("Cloudinary não configurado - usando URLs locais")

class WhatsAppFileManager:
    """
    Gerenciador de arquivos para WhatsApp via UltraMsg
    """
    
    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080")
        self.static_files_dir = os.path.join(os.path.dirname(__file__), "static_files")
        
        # Criar diretório se não existir
        os.makedirs(self.static_files_dir, exist_ok=True)
    
    def upload_file_to_public_url(self, file_path: str) -> Optional[str]:
        """
        Faz upload de arquivo para URL pública
        
        Args:
            file_path: Caminho do arquivo local
            
        Returns:
            URL pública do arquivo ou None se falhar
        """
        try:
            if CLOUDINARY_AVAILABLE:
                return self._upload_to_cloudinary(file_path)
            else:
                return self._copy_to_static_files(file_path)
                
        except Exception as e:
            logger.error(f"Erro ao fazer upload do arquivo: {str(e)}")
            return None
    
    def _upload_to_cloudinary(self, file_path: str) -> Optional[str]:
        """
        Faz upload para Cloudinary
        """
        try:
            # Determinar tipo de recurso
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                resource_type = "image"
            elif file_ext in ['.mp4', '.avi', '.mov']:
                resource_type = "video"
            elif file_ext in ['.mp3', '.wav', '.ogg']:
                resource_type = "video"  # Cloudinary trata áudio como video
            else:
                resource_type = "raw"  # Para PDFs e outros documentos
            
            # Fazer upload
            result = cloudinary.uploader.upload(
                file_path,
                resource_type=resource_type,
                folder="whatsapp_files"
            )
            
            logger.info(f"Arquivo enviado para Cloudinary: {result['secure_url']}")
            return result['secure_url']
            
        except Exception as e:
            logger.error(f"Erro no upload para Cloudinary: {str(e)}")
            return None
    
    def _copy_to_static_files(self, file_path: str) -> Optional[str]:
        """
        Copia arquivo para diretório static_files local
        """
        try:
            import shutil
            
            filename = os.path.basename(file_path)
            destination = os.path.join(self.static_files_dir, filename)
            
            # Copiar arquivo
            shutil.copy2(file_path, destination)
            
            # Retornar URL pública
            public_url = f"{self.base_url}/static_files/{filename}"
            logger.info(f"Arquivo copiado para static_files: {public_url}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Erro ao copiar arquivo: {str(e)}")
            return None
    
    def send_pdf_to_whatsapp(self, phone_number: str, pdf_path: str, dados_animal: Dict[str, Any] = None) -> bool:
        """
        Envia PDF via WhatsApp usando UltraMsg
        
        Args:
            phone_number: Número do telefone
            pdf_path: Caminho do arquivo PDF
            dados_animal: Dados do animal (opcional)
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Fazer upload do PDF para URL pública
            pdf_url = self.upload_file_to_public_url(pdf_path)
            
            if not pdf_url:
                logger.error("Não foi possível obter URL pública para o PDF")
                return False
            
            # Preparar nome do arquivo e caption
            if dados_animal and dados_animal.get('nome_animal'):
                nome_animal = dados_animal['nome_animal']
                filename = f"cotacao_{nome_animal.replace(' ', '_')}.pdf"
                caption = f"📄 Cotação de Seguro - {nome_animal}\n\nAqui está sua cotação completa com todos os detalhes!"
            else:
                filename = "cotacao_seguro.pdf"
                caption = "📄 Cotação de Seguro\n\nAqui está sua cotação completa!"
            
            # Enviar documento via UltraMsg
            result = ultramsg_api.send_document(phone_number, pdf_url, filename, caption)
            
            if result.get("success"):
                logger.info(f"PDF enviado com sucesso para {phone_number}")
                
                # Enviar mensagem de acompanhamento
                follow_up_message = """✅ **Cotação enviada com sucesso!**

📋 **O que você encontrará no documento:**
• Detalhes completos da cobertura
• Valor do prêmio anual
• Condições gerais do seguro
• Instruções para contratação
• Dados de contato para dúvidas

💬 **Próximos passos:**
Se desejar contratar o seguro ou tiver alguma dúvida, nosso agente entrará em contato em breve.

🙏 **Obrigado por escolher a Equinos Seguros!**"""
                
                # Enviar mensagem de acompanhamento
                ultramsg_api.send_text_message(phone_number, follow_up_message)
                
                return True
            else:
                logger.error(f"Erro ao enviar PDF via UltraMsg: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar PDF para WhatsApp: {str(e)}")
            return False
    
    def send_image_to_whatsapp(self, phone_number: str, image_path: str, caption: str = "") -> bool:
        """
        Envia imagem via WhatsApp usando UltraMsg
        
        Args:
            phone_number: Número do telefone
            image_path: Caminho da imagem
            caption: Legenda da imagem
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Fazer upload da imagem para URL pública
            image_url = self.upload_file_to_public_url(image_path)
            
            if not image_url:
                logger.error("Não foi possível obter URL pública para a imagem")
                return False
            
            # Enviar imagem via UltraMsg
            result = ultramsg_api.send_image(phone_number, image_url, caption)
            
            if result.get("success"):
                logger.info(f"Imagem enviada com sucesso para {phone_number}")
                return True
            else:
                logger.error(f"Erro ao enviar imagem via UltraMsg: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar imagem para WhatsApp: {str(e)}")
            return False
    
    def send_audio_to_whatsapp(self, phone_number: str, audio_path: str) -> bool:
        """
        Envia áudio via WhatsApp usando UltraMsg
        
        Args:
            phone_number: Número do telefone
            audio_path: Caminho do arquivo de áudio
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Fazer upload do áudio para URL pública
            audio_url = self.upload_file_to_public_url(audio_path)
            
            if not audio_url:
                logger.error("Não foi possível obter URL pública para o áudio")
                return False
            
            # Enviar áudio via UltraMsg
            result = ultramsg_api.send_audio(phone_number, audio_url)
            
            if result.get("success"):
                logger.info(f"Áudio enviado com sucesso para {phone_number}")
                return True
            else:
                logger.error(f"Erro ao enviar áudio via UltraMsg: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar áudio para WhatsApp: {str(e)}")
            return False
    
    def send_document_to_whatsapp(self, phone_number: str, document_path: str, 
                                 filename: str = None, caption: str = "") -> bool:
        """
        Envia documento genérico via WhatsApp usando UltraMsg
        
        Args:
            phone_number: Número do telefone
            document_path: Caminho do documento
            filename: Nome do arquivo (opcional)
            caption: Legenda do documento
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            # Fazer upload do documento para URL pública
            document_url = self.upload_file_to_public_url(document_path)
            
            if not document_url:
                logger.error("Não foi possível obter URL pública para o documento")
                return False
            
            # Usar nome do arquivo original se não fornecido
            if not filename:
                filename = os.path.basename(document_path)
            
            # Enviar documento via UltraMsg
            result = ultramsg_api.send_document(phone_number, document_url, filename, caption)
            
            if result.get("success"):
                logger.info(f"Documento enviado com sucesso para {phone_number}")
                return True
            else:
                logger.error(f"Erro ao enviar documento via UltraMsg: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar documento para WhatsApp: {str(e)}")
            return False

# Instância global
file_manager = WhatsAppFileManager()

# Funções de compatibilidade com código existente
def send_pdf_to_whatsapp(phone_number: str, pdf_path: str, dados_animal: Dict[str, Any] = None) -> bool:
    """
    Função de compatibilidade para envio de PDF
    """
    return file_manager.send_pdf_to_whatsapp(phone_number, pdf_path, dados_animal)

def upload_file_to_public_url(file_path: str) -> Optional[str]:
    """
    Função de compatibilidade para upload de arquivo
    """
    return file_manager.upload_file_to_public_url(file_path)

def send_image_to_whatsapp(phone_number: str, image_path: str, caption: str = "") -> bool:
    """
    Função de compatibilidade para envio de imagem
    """
    return file_manager.send_image_to_whatsapp(phone_number, image_path, caption)

def send_audio_to_whatsapp(phone_number: str, audio_path: str) -> bool:
    """
    Função de compatibilidade para envio de áudio
    """
    return file_manager.send_audio_to_whatsapp(phone_number, audio_path)

def send_document_to_whatsapp(phone_number: str, document_path: str, 
                             filename: str = None, caption: str = "") -> bool:
    """
    Função de compatibilidade para envio de documento
    """
    return file_manager.send_document_to_whatsapp(phone_number, document_path, filename, caption)

