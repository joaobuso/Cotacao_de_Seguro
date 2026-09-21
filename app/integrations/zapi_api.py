# -*- coding: utf-8 -*-

import os
import re
import base64
import logging
import mimetypes
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class ZApiAPI:
    """
    Adapter da Z-API mantendo a mesma interface usada pelo bot:
    - send_message(phone, message)
    - send_document(phone, file_path, caption)
    """

    def __init__(self):
        self.instance_id = os.getenv("ZAPI_INSTANCE_ID")
        self.token = os.getenv("ZAPI_TOKEN")
        self.client_token = os.getenv("ZAPI_CLIENT_TOKEN")
        self.base_url = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io/instances").rstrip("/")

        if not self.instance_id:
            logger.warning("ZAPI_INSTANCE_ID não configurado")
        if not self.token:
            logger.warning("ZAPI_TOKEN não configurado")
        if not self.client_token:
            logger.warning("ZAPI_CLIENT_TOKEN não configurado")

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Client-Token": self.client_token or ""
        }

    def _url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{self.instance_id}/token/{self.token}/{endpoint}"

    def _normalize_phone(self, phone: str) -> str:
        """
        Z-API espera telefone somente com números:
        Ex: 5511999999999
        """
        phone = str(phone or "")
        phone = re.sub(r"\D", "", phone)

        if not phone.startswith("55"):
            phone = "55" + phone

        return phone

    def send_message(self, phone: str, message: str):
        """
        Envia texto simples.
        """
        phone = self._normalize_phone(phone)

        payload = {
            "phone": phone,
            "message": message
        }

        url = self._url("send-text")

        logger.info("Enviando mensagem Z-API para %s", phone)

        response = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=60
        )

        logger.info(
            "Resposta Z-API send_message | status=%s | body=%s",
            response.status_code,
            response.text[:1000]
        )

        if not response.ok:
            logger.error(
                "Erro Z-API send_message: HTTP %s - %s",
                response.status_code,
                response.text[:1000]
            )
            response.raise_for_status()

        logger.info("Mensagem Z-API enviada para %s: %s", phone, message[:80])

        try:
            return response.json()
        except Exception:
            return {"status_code": response.status_code, "text": response.text}

    def send_document(self, phone: str, file_path: str, caption: str = None):
        """
        Envia documento PDF pela Z-API.

        Endpoint correto:
        /send-document/pdf

        Body:
        {
            "phone": "...",
            "document": "data:application/pdf;base64,...",
            "fileName": "arquivo.pdf",
            "caption": "opcional"
        }
        """
        phone = self._normalize_phone(phone)
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/pdf"

        extension = file_path.suffix.replace(".", "").lower() or "pdf"

        # Para PDF, força o endpoint correto da Z-API
        if extension == "pdf":
            endpoint = "send-document/pdf"
        else:
            endpoint = f"send-document/{extension}"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        encoded = base64.b64encode(file_bytes).decode("utf-8")
        base64_document = f"data:{mime_type};base64,{encoded}"

        payload = {
            "phone": phone,
            "document": base64_document,
            "fileName": file_path.name
        }

        if caption:
            payload["caption"] = caption

        url = self._url(endpoint)

        logger.info(
            "Enviando documento Z-API para %s | endpoint=%s | arquivo=%s | mime=%s | bytes=%s",
            phone,
            endpoint,
            file_path.name,
            mime_type,
            len(file_bytes)
        )

        response = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=120
        )

        response_text = response.text[:2000]

        logger.info(
            "Resposta Z-API send_document | status=%s | body=%s",
            response.status_code,
            response_text
        )

        if not response.ok:
            logger.error(
                "Erro Z-API send_document: HTTP %s - %s",
                response.status_code,
                response_text
            )
            response.raise_for_status()

        try:
            response_json = response.json()
        except Exception:
            response_json = {
                "status_code": response.status_code,
                "text": response.text
            }

        logger.info(
            "Documento Z-API aceito para envio | phone=%s | arquivo=%s | response=%s",
            phone,
            file_path.name,
            response_json
        )

        return response_json