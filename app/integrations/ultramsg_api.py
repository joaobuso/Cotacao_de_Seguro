# -*- coding: utf-8 -*-
"""
Integração com a API UltraMsg para WhatsApp
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

class UltraMsgAPI:
    """
    Cliente para a API UltraMsg
    """
    
    def __init__(self):
        self.instance_id = os.getenv('ULTRAMSG_INSTANCE_ID')
        self.token = os.getenv('ULTRAMSG_TOKEN')
        self.base_url = f"https://api.ultramsg.com/{self.instance_id}"
        
        if not self.instance_id or not self.token:
            logger.error("ULTRAMSG_INSTANCE_ID e ULTRAMSG_TOKEN devem estar configurados")
            raise ValueError("Credenciais UltraMsg não configuradas")
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz requisição para a API UltraMsg
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Adicionar token aos dados
            data['token'] = self.token
            
            # Preparar payload
            payload = "&".join([f"{k}={quote(str(v))}" for k, v in data.items()])
            payload = payload.encode('utf8').decode('iso-8859-1')
            
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Requisição UltraMsg bem-sucedida: {endpoint}")
                return {"success": True, "data": result}
            else:
                logger.error(f"Erro na requisição UltraMsg: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição UltraMsg")
            return {"success": False, "error": "Timeout na requisição"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão UltraMsg: {str(e)}")
            return {"success": False, "error": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado UltraMsg: {str(e)}")
            return {"success": False, "error": f"Erro inesperado: {str(e)}"}
    
    def send_text_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envia mensagem de texto
        
        Args:
            phone: Número do telefone (formato: +5519988118043)
            message: Texto da mensagem
            
        Returns:
            Dict com resultado da operação
        """
        try:
            # Limpar e formatar número
            phone = self._format_phone(phone)
            
            data = {
                "to": phone,
                "body": message
            }
            
            result = self._make_request("messages/chat", data)
            
            if result["success"]:
                logger.info(f"Mensagem enviada para {phone}: {message[:50]}...")
            else:
                logger.error(f"Erro ao enviar mensagem para {phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de texto: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_image(self, phone: str, image_url: str, caption: str = "") -> Dict[str, Any]:
        """
        Envia imagem
        
        Args:
            phone: Número do telefone
            image_url: URL da imagem
            caption: Legenda da imagem
            
        Returns:
            Dict com resultado da operação
        """
        try:
            phone = self._format_phone(phone)
            
            data = {
                "to": phone,
                "image": image_url,
                "caption": caption
            }
            
            result = self._make_request("messages/image", data)
            
            if result["success"]:
                logger.info(f"Imagem enviada para {phone}")
            else:
                logger.error(f"Erro ao enviar imagem para {phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_document(self, phone: str, document_url: str, filename: str, caption: str = "") -> Dict[str, Any]:
        """
        Envia documento
        
        Args:
            phone: Número do telefone
            document_url: URL do documento
            filename: Nome do arquivo
            caption: Legenda do documento
            
        Returns:
            Dict com resultado da operação
        """
        try:
            phone = self._format_phone(phone)
            
            data = {
                "to": phone,
                "document": document_url,
                "filename": filename,
                "caption": caption
            }
            
            result = self._make_request("messages/document", data)
            
            if result["success"]:
                logger.info(f"Documento enviado para {phone}: {filename}")
            else:
                logger.error(f"Erro ao enviar documento para {phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar documento: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """
        Envia áudio
        
        Args:
            phone: Número do telefone
            audio_url: URL do áudio
            
        Returns:
            Dict com resultado da operação
        """
        try:
            phone = self._format_phone(phone)
            
            data = {
                "to": phone,
                "audio": audio_url
            }
            
            result = self._make_request("messages/voice", data)
            
            if result["success"]:
                logger.info(f"Áudio enviado para {phone}")
            else:
                logger.error(f"Erro ao enviar áudio para {phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar áudio: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_instance_status(self) -> Dict[str, Any]:
        """
        Verifica status da instância
        
        Returns:
            Dict com status da instância
        """
        try:
            data = {}
            result = self._make_request("instance/status", data)
            
            if result["success"]:
                logger.info("Status da instância verificado")
            else:
                logger.warning(f"Erro ao verificar status: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da instância: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _format_phone(self, phone: str) -> str:
        """
        Formata número de telefone para o padrão UltraMsg
        
        Args:
            phone: Número do telefone
            
        Returns:
            Número formatado
        """
        # Remover caracteres especiais
        phone = ''.join(filter(str.isdigit, phone))
        
        # Adicionar código do país se não tiver
        if not phone.startswith('55'):
            phone = '55' + phone
        
        # Adicionar + no início
        if not phone.startswith('+'):
            phone = '+' + phone
        
        return phone

# Instância global da API
ultramsg_api = UltraMsgAPI()

