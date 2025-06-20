import os
import requests
import tempfile
from gtts import gTTS
from datetime import datetime
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Configurar a API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def convert_user_audio_to_text(audio_url):
    """
    Converte um áudio de voz do usuário para texto usando a API Whisper da OpenAI.
    Retorna o texto transcrito ou None em caso de erro.
    """
    try:
        print(f"Iniciando transcrição de áudio de {audio_url}")
        
        # Baixar o arquivo de áudio
        response = requests.get(audio_url)
        if response.status_code != 200:
            print(f"Erro ao baixar áudio: Status {response.status_code}")
            return None
        
        # Criar arquivo temporário para o áudio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_audio:
            temp_audio.write(response.content)
            temp_audio_path = temp_audio.name
        
        try:
            # Usar a API Whisper da OpenAI para transcrever
            with open(temp_audio_path, 'rb') as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"  # Português
                )
            
            transcribed_text = transcript.text.strip()
            print(f"Áudio transcrito com sucesso: {transcribed_text}")
            return transcribed_text
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return None

def generate_bot_audio_response(text):
    """
    Gera um arquivo de áudio a partir do texto da resposta do bot.
    Retorna o nome do arquivo gerado ou None em caso de erro.
    """
    try:
        # Criar diretório para áudios se não existir
        static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_bot_audio")
        os.makedirs(static_folder, exist_ok=True)
        
        # Gerar nome de arquivo único
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"bot_response_{timestamp}.mp3"
        filepath = os.path.join(static_folder, filename)
        
        # Gerar áudio usando gTTS
        tts = gTTS(text=text, lang='pt-br', slow=False)
        tts.save(filepath)
        
        print(f"Áudio gerado: {filepath}")
        return filename
    except Exception as e:
        print(f"Erro ao gerar áudio: {e}")
        return None

def cleanup_old_audio_files(max_age_hours=24):
    """
    Remove arquivos de áudio antigos para economizar espaço.
    Remove arquivos com mais de max_age_hours horas.
    """
    try:
        static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_bot_audio")
        if not os.path.exists(static_folder):
            return
        
        current_time = datetime.now()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(static_folder):
            if filename.endswith('.mp3'):
                filepath = os.path.join(static_folder, filename)
                file_age = current_time.timestamp() - os.path.getmtime(filepath)
                
                if file_age > max_age_seconds:
                    os.unlink(filepath)
                    print(f"Arquivo de áudio antigo removido: {filename}")
                    
    except Exception as e:
        print(f"Erro ao limpar arquivos de áudio antigos: {e}")

