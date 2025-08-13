# -*- coding: utf-8 -*-
"""
Gerenciador de arquivos para upload e envio via WhatsApp
"""

import os
import logging
import shutil
from typing import Optional, Dict, Any
from app.integrations.ultramsg_api import ultramsg_api

logger = logging.getLogger(__name__)

class FileManager:
    """
    Classe para gerenciar upload e envio de arquivos
    """
    
    def __init__(self):
        self.base_url = os.getenv('BASE_URL', 'http://localhost:10000')
        self.static_files_dir = os.path.join(os.getcwd(), 'static_files')
        self.cloudinary_enabled = self._check_cloudinary()
        
        # Criar diretório se não existir
        os.makedirs(self.static_files_dir, exist_ok=True)
    
    def _check_cloudinary(self) -> bool:
        """
        Verifica se Cloudinary está configurado
        """
        try:
            import cloudinary
            import cloudinary.uploader
            
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
            api_key = os.getenv('CLOUDINARY_API_KEY')
            api_secret = os.getenv('CLOUDINARY_API_SECRET')
            
            if cloud_name and api_key and api_secret:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret
                )
                logger.info("✅ Cloudinary configurado")
                return True
            else:
                logger.info("📁 Cloudinary não configurado - usando URLs locais")
                return False
                
        except ImportError:
            logger.info("📁 Cloudinary não instalado - usando URLs locais")
            return False
    
    def upload_file_to_public_url(self, file_path: str) -> Optional[str]:
        """
        Faz upload de arquivo para URL pública
        
        Args:
            file_path: Caminho do arquivo local
            
        Returns:
            URL pública do arquivo ou None se falhar
        """
        try:
            if self.cloudinary_enabled:
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
            import cloudinary.uploader
            
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
                folder="whatsapp_files",
                use_filename=True,
                unique_filename=True
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
    
    def send_pdf_to_whatsapp(self, phone_number: str, pdf_path: str, 
                            dados_animal: Dict[str, Any] = None) -> bool:
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
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Remove arquivos antigos do diretório static_files
        
        Args:
            max_age_hours: Idade máxima em horas
        """
        try:
            import time
            
            if not os.path.exists(self.static_files_dir):
                return
            
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            removed_count = 0
            for filename in os.listdir(self.static_files_dir):
                file_path = os.path.join(self.static_files_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Removidos {removed_count} arquivos antigos")
                
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos: {str(e)}")
    
    def get_file_url(self, filename: str) -> str:
        """
        Retorna URL pública do arquivo
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            URL pública do arquivo
        """
        return f"{self.base_url}/static_files/{filename}"
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        Retorna tamanho do arquivo em bytes
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Tamanho em bytes ou None se erro
        """
        try:
            return os.path.getsize(file_path)
        except:
            return None
    
    def is_file_type_supported(self, file_path: str, file_type: str) -> bool:
        """
        Verifica se tipo de arquivo é suportado
        
        Args:
            file_path: Caminho do arquivo
            file_type: Tipo esperado (image, audio, document)
            
        Returns:
            True se suportado
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        supported_types = {
            'image': ['.jpg', '.jpeg', '.png', '.gif'],
            'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.txt'],
            'video': ['.mp4', '.avi', '.mov']
        }
        
        return file_ext in supported_types.get(file_type, [])

