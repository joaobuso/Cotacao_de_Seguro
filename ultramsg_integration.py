# -*- coding: utf-8 -*-
"""
Módulo de integração com UltraMsg API - Versão Melhorada
Substitui o Twilio para comunicação WhatsApp com funcionalidades completas
"""

import os
import requests
import logging
import json
import time
from typing import Optional, Dict, Any, List
from urllib.parse import quote

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraMsgAPI:
    """Classe para integração completa com UltraMsg WhatsApp API"""
    
    def __init__(self):
        # Configurações da API
        self.instance_id = os.getenv("ULTRAMSG_INSTANCE_ID")
        self.token = os.getenv("ULTRAMSG_TOKEN")
        
        if not self.instance_id or not self.token:
            raise ValueError("ULTRAMSG_INSTANCE_ID e ULTRAMSG_TOKEN devem estar configurados nas variáveis de ambiente")
        
        self.base_url = f"https://api.ultramsg.com/{self.instance_id}"
        
        # Headers padrão
        self.headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        
        # Configurações de retry
        self.max_retries = 3
        self.retry_delay = 2
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Formata número de telefone para UltraMsg
        Remove prefixos como 'whatsapp:' e formata corretamente
        
        Args:
            phone: Número original (pode ter prefixos do Twilio)
            
        Returns:
            Número formatado para UltraMsg
        """
        # Remove prefixos do Twilio e espaços
        clean_phone = phone.replace("whatsapp:", "").replace("+", "").strip()
        
        # Remove caracteres especiais
        clean_phone = ''.join(filter(str.isdigit, clean_phone))
        
        # Garante que tenha o código do país (Brasil = 55)
        if len(clean_phone) == 11 and clean_phone.startswith("11"):
            # Número de São Paulo sem código do país
            clean_phone = "55" + clean_phone
        elif len(clean_phone) == 10:
            # Número sem DDD e código do país
            clean_phone = "5511" + clean_phone
        elif not clean_phone.startswith("55"):
            # Adiciona código do país se não tiver
            clean_phone = "55" + clean_phone
        
        # Adiciona o + no início
        return "+" + clean_phone
    
    def _make_request(self, endpoint: str, payload: str, retries: int = 0) -> Dict[str, Any]:
        """
        Faz requisição para a API com retry automático
        
        Args:
            endpoint: Endpoint da API
            payload: Dados da requisição
            retries: Número de tentativas já realizadas
            
        Returns:
            Resposta da API
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Fazer requisição
            response = requests.post(url, data=payload, headers=self.headers, timeout=30)
            
            # Log da requisição
            logger.info(f"Requisição para {endpoint}: Status {response.status_code}")
            
            # Verificar se foi bem-sucedida
            if response.status_code == 200:
                try:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response.json() if response.text else {},
                        "raw_response": response.text
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": {"message": response.text},
                        "raw_response": response.text
                    }
            else:
                # Erro na requisição
                error_response = {
                    "success": False,
                    "status_code": response.status_code,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "raw_response": response.text
                }
                
                # Tentar novamente se não excedeu o limite
                if retries < self.max_retries:
                    logger.warning(f"Erro na requisição, tentando novamente em {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    return self._make_request(endpoint, payload, retries + 1)
                
                return error_response
                
        except requests.exceptions.Timeout:
            error_msg = "Timeout na requisição"
            logger.error(error_msg)
            
            if retries < self.max_retries:
                time.sleep(self.retry_delay)
                return self._make_request(endpoint, payload, retries + 1)
            
            return {"success": False, "error": error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição: {str(e)}"
            logger.error(error_msg)
            
            if retries < self.max_retries:
                time.sleep(self.retry_delay)
                return self._make_request(endpoint, payload, retries + 1)
            
            return {"success": False, "error": error_msg}
    
    def send_text_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envia mensagem de texto via UltraMsg
        
        Args:
            phone: Número do telefone
            message: Texto da mensagem
            
        Returns:
            Dict com resposta da API
        """
        try:
            # Formatar número
            formatted_phone = self._format_phone_number(phone)
            
            # Escapar caracteres especiais na mensagem
            escaped_message = quote(message, safe='')
            
            # Payload
            payload = f"token={self.token}&to={formatted_phone}&body={escaped_message}"
            
            # Fazer requisição
            result = self._make_request("messages/chat", payload)
            result["phone"] = formatted_phone
            result["original_phone"] = phone
            
            if result["success"]:
                logger.info(f"Mensagem enviada para {formatted_phone}")
            else:
                logger.error(f"Erro ao enviar mensagem para {formatted_phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }
    
    def send_document(self, phone: str, document_url: str, filename: str, caption: str = "") -> Dict[str, Any]:
        """
        Envia documento (PDF, imagem, etc.) via UltraMsg
        
        Args:
            phone: Número do telefone
            document_url: URL do documento (deve ser acessível publicamente)
            filename: Nome do arquivo
            caption: Legenda do documento
            
        Returns:
            Dict com resposta da API
        """
        try:
            # Formatar número
            formatted_phone = self._format_phone_number(phone)
            
            # Escapar caracteres especiais
            escaped_filename = quote(filename, safe='')
            escaped_caption = quote(caption, safe='') if caption else ""
            escaped_url = quote(document_url, safe=':/?#[]@!$&\'()*+,;=')
            
            # Payload
            payload = f"token={self.token}&to={formatted_phone}&document={escaped_url}&filename={escaped_filename}"
            if caption:
                payload += f"&caption={escaped_caption}"
            
            # Fazer requisição
            result = self._make_request("messages/document", payload)
            result["phone"] = formatted_phone
            result["original_phone"] = phone
            
            if result["success"]:
                logger.info(f"Documento enviado para {formatted_phone}: {filename}")
            else:
                logger.error(f"Erro ao enviar documento para {formatted_phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar documento: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }
    
    def send_image(self, phone: str, image_url: str, caption: str = "") -> Dict[str, Any]:
        """
        Envia imagem via UltraMsg
        
        Args:
            phone: Número do telefone
            image_url: URL da imagem
            caption: Legenda da imagem
            
        Returns:
            Dict com resposta da API
        """
        try:
            # Formatar número
            formatted_phone = self._format_phone_number(phone)
            
            # Escapar caracteres especiais
            escaped_caption = quote(caption, safe='') if caption else ""
            escaped_url = quote(image_url, safe=':/?#[]@!$&\'()*+,;=')
            
            # Payload
            payload = f"token={self.token}&to={formatted_phone}&image={escaped_url}"
            if caption:
                payload += f"&caption={escaped_caption}"
            
            # Fazer requisição
            result = self._make_request("messages/image", payload)
            result["phone"] = formatted_phone
            result["original_phone"] = phone
            
            if result["success"]:
                logger.info(f"Imagem enviada para {formatted_phone}")
            else:
                logger.error(f"Erro ao enviar imagem para {formatted_phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }
    
    def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """
        Envia áudio via UltraMsg
        
        Args:
            phone: Número do telefone
            audio_url: URL do áudio
            
        Returns:
            Dict com resposta da API
        """
        try:
            # Formatar número
            formatted_phone = self._format_phone_number(phone)
            
            # Escapar URL
            escaped_url = quote(audio_url, safe=':/?#[]@!$&\'()*+,;=')
            
            # Payload
            payload = f"token={self.token}&to={formatted_phone}&audio={escaped_url}"
            
            # Fazer requisição
            result = self._make_request("messages/audio", payload)
            result["phone"] = formatted_phone
            result["original_phone"] = phone
            
            if result["success"]:
                logger.info(f"Áudio enviado para {formatted_phone}")
            else:
                logger.error(f"Erro ao enviar áudio para {formatted_phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar áudio: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }
    
    def send_location(self, phone: str, latitude: float, longitude: float, address: str = "") -> Dict[str, Any]:
        """
        Envia localização via UltraMsg
        
        Args:
            phone: Número do telefone
            latitude: Latitude
            longitude: Longitude
            address: Endereço (opcional)
            
        Returns:
            Dict com resposta da API
        """
        try:
            # Formatar número
            formatted_phone = self._format_phone_number(phone)
            
            # Escapar endereço
            escaped_address = quote(address, safe='') if address else ""
            
            # Payload
            payload = f"token={self.token}&to={formatted_phone}&lat={latitude}&lng={longitude}"
            if address:
                payload += f"&address={escaped_address}"
            
            # Fazer requisição
            result = self._make_request("messages/location", payload)
            result["phone"] = formatted_phone
            result["original_phone"] = phone
            
            if result["success"]:
                logger.info(f"Localização enviada para {formatted_phone}")
            else:
                logger.error(f"Erro ao enviar localização para {formatted_phone}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao enviar localização: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }
    
    def get_instance_status(self) -> Dict[str, Any]:
        """
        Verifica status da instância UltraMsg
        
        Returns:
            Dict com status da instância
        """
        try:
            payload = f"token={self.token}"
            result = self._make_request("instance/status", payload)
            
            if result["success"]:
                logger.info("Status da instância obtido com sucesso")
            else:
                logger.error(f"Erro ao obter status da instância: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da instância: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_contacts(self) -> Dict[str, Any]:
        """
        Obtém lista de contatos
        
        Returns:
            Dict com lista de contatos
        """
        try:
            payload = f"token={self.token}"
            result = self._make_request("contacts", payload)
            
            if result["success"]:
                logger.info("Lista de contatos obtida com sucesso")
            else:
                logger.error(f"Erro ao obter contatos: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter contatos: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_bulk_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Envia múltiplas mensagens em lote
        
        Args:
            messages: Lista de dicts com 'phone' e 'message'
            
        Returns:
            Lista com resultados de cada envio
        """
        results = []
        
        for msg_data in messages:
            phone = msg_data.get("phone")
            message = msg_data.get("message")
            
            if phone and message:
                result = self.send_text_message(phone, message)
                results.append(result)
                
                # Pequeno delay entre mensagens para evitar rate limiting
                time.sleep(0.5)
            else:
                results.append({
                    "success": False,
                    "error": "Phone ou message não fornecidos",
                    "phone": phone
                })
        
        return results

# Classe para compatibilidade com código Twilio existente
class TwilioToUltraMsgAdapter:
    """
    Adapter para facilitar migração do Twilio para UltraMsg
    Mantém interface similar ao Twilio
    """
    
    def __init__(self):
        self.ultramsg = UltraMsgAPI()
    
    def send_message(self, to: str, body: str, media_url: str = None) -> Dict[str, Any]:
        """
        Envia mensagem (compatível com interface Twilio)
        
        Args:
            to: Número de destino
            body: Texto da mensagem
            media_url: URL de mídia (opcional)
            
        Returns:
            Resultado do envio
        """
        if media_url:
            # Determinar tipo de mídia pela extensão
            if any(ext in media_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                return self.ultramsg.send_image(to, media_url, body)
            elif any(ext in media_url.lower() for ext in ['.pdf', '.doc', '.docx']):
                return self.ultramsg.send_document(to, media_url, "documento.pdf", body)
            elif any(ext in media_url.lower() for ext in ['.mp3', '.wav', '.ogg']):
                return self.ultramsg.send_audio(to, media_url)
            else:
                # Tentar como documento genérico
                return self.ultramsg.send_document(to, media_url, "arquivo", body)
        else:
            return self.ultramsg.send_text_message(to, body)

# Instâncias globais para uso em todo o projeto
ultramsg_api = UltraMsgAPI()
twilio_adapter = TwilioToUltraMsgAdapter()

# Função de conveniência para migração rápida
def send_whatsapp_message(phone: str, message: str, media_url: str = None) -> bool:
    """
    Função simples para enviar mensagem WhatsApp
    
    Args:
        phone: Número do telefone
        message: Mensagem de texto
        media_url: URL de mídia opcional
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        if media_url:
            result = twilio_adapter.send_message(phone, message, media_url)
        else:
            result = ultramsg_api.send_text_message(phone, message)
        
        return result.get("success", False)
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        return False

