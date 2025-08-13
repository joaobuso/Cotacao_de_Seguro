# -*- coding: utf-8 -*-
"""
Processador de áudio para transcrição e geração
"""

import os
import logging
import requests
import openai
from typing import Optional
from gtts import gTTS
import tempfile

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Classe para processar áudios (transcrição e geração)
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.tts_enabled = os.getenv('TTS_ENABLED', 'True').lower() == 'true'
        self.tts_language = os.getenv('TTS_LANGUAGE', 'pt-BR')
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        else:
            logger.warning("OPENAI_API_KEY não configurado - transcrição desabilitada")
    
    def transcribe_audio(self, audio_url: str) -> Optional[str]:
        """
        Transcreve áudio usando OpenAI Whisper
        
        Args:
            audio_url: URL do arquivo de áudio
            
        Returns:
            Texto transcrito ou None se falhar
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key não configurado")
            return None
        
        try:
            # Baixar arquivo de áudio
            audio_file = self._download_audio(audio_url)
            if not audio_file:
                return None
            
            # Transcrever usando Whisper
            with open(audio_file, 'rb') as f:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="pt"
                )
            
            # Limpar arquivo temporário
            os.unlink(audio_file)
            
            transcribed_text = transcript.text.strip()
            logger.info(f"Áudio transcrito: {transcribed_text[:100]}...")
            
            return transcribed_text if transcribed_text else None
            
        except Exception as e:
            logger.error(f"Erro na transcrição de áudio: {str(e)}")
            return None
    
    def _download_audio(self, audio_url: str) -> Optional[str]:
        """
        Baixa arquivo de áudio temporariamente
        """
        try:
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            logger.info(f"Áudio baixado: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Erro ao baixar áudio: {str(e)}")
            return None
    
    def generate_speech(self, text: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Gera áudio a partir de texto usando gTTS
        
        Args:
            text: Texto para converter em áudio
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo de áudio gerado ou None se falhar
        """
        if not self.tts_enabled:
            logger.info("TTS desabilitado")
            return None
        
        try:
            # Limitar tamanho do texto
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Gerar nome do arquivo se não fornecido
            if not filename:
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                filename = f"tts_{text_hash}.mp3"
            
            # Caminho completo
            audio_dir = os.path.join(os.getcwd(), 'static_bot_audio')
            os.makedirs(audio_dir, exist_ok=True)
            audio_path = os.path.join(audio_dir, filename)
            
            # Verificar se arquivo já existe
            if os.path.exists(audio_path):
                logger.info(f"Áudio já existe: {filename}")
                return filename
            
            # Gerar áudio
            tts = gTTS(text=text, lang=self.tts_language.split('-')[0], slow=False)
            tts.save(audio_path)
            
            logger.info(f"Áudio gerado: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar áudio: {str(e)}")
            return None
    
    def generate_speech_openai(self, text: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Gera áudio usando OpenAI TTS (mais natural)
        
        Args:
            text: Texto para converter
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo ou None se falhar
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key não configurado")
            return self.generate_speech(text, filename)  # Fallback para gTTS
        
        try:
            # Limitar tamanho do texto
            if len(text) > 4000:  # Limite da OpenAI
                text = text[:4000] + "..."
            
            # Gerar nome do arquivo se não fornecido
            if not filename:
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                filename = f"openai_tts_{text_hash}.mp3"
            
            # Caminho completo
            audio_dir = os.path.join(os.getcwd(), 'static_bot_audio')
            os.makedirs(audio_dir, exist_ok=True)
            audio_path = os.path.join(audio_dir, filename)
            
            # Verificar se arquivo já existe
            if os.path.exists(audio_path):
                logger.info(f"Áudio já existe: {filename}")
                return filename
            
            # Gerar áudio com OpenAI
            response = openai.audio.speech.create(
                model="tts-1",
                voice="alloy",  # Voz mais neutra
                input=text
            )
            
            # Salvar arquivo
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Áudio OpenAI gerado: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar áudio OpenAI: {str(e)}")
            # Fallback para gTTS
            return self.generate_speech(text, filename)
    
    def cleanup_old_audio_files(self, max_age_hours: int = 24):
        """
        Remove arquivos de áudio antigos
        
        Args:
            max_age_hours: Idade máxima em horas
        """
        try:
            import time
            
            audio_dir = os.path.join(os.getcwd(), 'static_bot_audio')
            if not os.path.exists(audio_dir):
                return
            
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            removed_count = 0
            for filename in os.listdir(audio_dir):
                file_path = os.path.join(audio_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Removidos {removed_count} arquivos de áudio antigos")
                
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos de áudio: {str(e)}")
    
    def get_audio_url(self, filename: str) -> str:
        """
        Retorna URL pública do arquivo de áudio
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            URL pública do arquivo
        """
        base_url = os.getenv('BASE_URL', 'http://localhost:10000')
        return f"{base_url}/static_audio/{filename}"

