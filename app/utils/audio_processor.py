# /home/ubuntu/whatsapp_handoff_project/app/utils/audio_processor.py
import os
import hashlib
import glob
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("AVISO: OPENAI_API_KEY não configurada no .env")
    # Em um app real, você pode querer lançar um erro ou desabilitar funcionalidades de IA

client = OpenAI(api_key=OPENAI_API_KEY)

# Diretório para salvar os áudios gerados pelo bot
# O Flask servirá arquivos desta pasta
BOT_AUDIO_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_bot_audio")
if not os.path.exists(BOT_AUDIO_CACHE_DIR):
    os.makedirs(BOT_AUDIO_CACHE_DIR)

TEMP_USER_AUDIO_PATH = "/tmp/temp_user_audio.ogg" # Caminho temporário para áudio do usuário

def convert_user_audio_to_text(media_url):
    """Baixa um arquivo de áudio da URL fornecida e o converte para texto usando Whisper."""
    if not OPENAI_API_KEY:
        return "Desculpe, o serviço de transcrição de áudio não está configurado."
    try:
        # Baixar o arquivo de áudio
        response = requests.get(media_url, timeout=10) # Adicionado timeout
        response.raise_for_status() # Levanta um erro para códigos de status ruins (4xx ou 5xx)
        
        with open(TEMP_USER_AUDIO_PATH, "wb") as f:
            f.write(response.content)

        # Chamar OpenAI Whisper
        with open(TEMP_USER_AUDIO_PATH, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Remover arquivo temporário após transcrição
        if os.path.exists(TEMP_USER_AUDIO_PATH):
            os.remove(TEMP_USER_AUDIO_PATH)
            
        return transcription
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o áudio: {str(e)}")
        return "Desculpe, houve um problema ao acessar seu áudio."
    except Exception as e:
        print(f"Erro na transcrição do áudio: {str(e)}")
        if os.path.exists(TEMP_USER_AUDIO_PATH):
            os.remove(TEMP_USER_AUDIO_PATH)
        return "Desculpe, não consegui interpretar seu áudio no momento."

def generate_bot_audio_response(text_to_speak, voice="nova"):
    """Gera um arquivo de áudio a partir do texto usando OpenAI TTS e retorna o nome do arquivo.
       Usa um cache para evitar gerar o mesmo áudio repetidamente."""
    if not OPENAI_API_KEY:
        return None # Ou um áudio padrão de erro, ou simplesmente não envia áudio

    try:
        # Gera hash do texto para identificar áudios únicos e evitar nomes de arquivo muito longos
        text_hash = hashlib.md5(text_to_speak.encode("utf-8")).hexdigest()
        audio_filename = f"bot_response_{text_hash}.mp3"
        audio_path = os.path.join(BOT_AUDIO_CACHE_DIR, audio_filename)

        # Se já existe o áudio no cache, não gera de novo
        if os.path.exists(audio_path):
            # print(f"Áudio encontrado no cache: {audio_filename}")
            return audio_filename

        # Gera novo áudio usando OpenAI TTS
        response = client.audio.speech.create(
            model="tts-1", # ou "tts-1-hd" para maior qualidade
            voice=voice,  # vozes disponíveis: alloy, echo, fable, onyx, nova, shimmer
            input=text_to_speak
        )

        with open(audio_path, "wb") as f:
            f.write(response.content)
        # print(f"Áudio gerado e salvo em: {audio_path}")

        # Opcional: limpar áudios antigos para evitar lotar disco
        _clear_old_cached_audios()

        return audio_filename
    except Exception as e:
        print(f"Erro ao gerar áudio da resposta do bot: {str(e)}")
        return None

def _clear_old_cached_audios(max_files=100, max_age_days=30):
    """Limpa áudios antigos do cache para economizar espaço."""
    try:
        files = glob.glob(os.path.join(BOT_AUDIO_CACHE_DIR, "bot_response_*.mp3"))
        files.sort(key=os.path.getmtime)
        
        # Limpar por número máximo de arquivos
        if len(files) > max_files:
            for file_to_delete in files[:len(files) - max_files]:
                try:
                    os.remove(file_to_delete)
                    # print(f"Cache de áudio antigo removido (excesso): {file_to_delete}")
                except Exception as e_remove:
                    print(f"Erro ao remover áudio do cache (excesso) {file_to_delete}: {str(e_remove)}")
        
        # Limpar por idade máxima (opcional, pode ser combinado ou usado separadamente)
        # now = datetime.now()
        # for f_path in files:
        #     if (now - datetime.fromtimestamp(os.path.getmtime(f_path))).days > max_age_days:
        #         try:
        #             os.remove(f_path)
        #             print(f"Cache de áudio antigo removido (idade): {f_path}")
        #         except Exception as e_remove_age:
        #             print(f"Erro ao remover áudio do cache (idade) {f_path}: {str(e_remove_age)}")

    except Exception as e:
        print(f"Erro ao limpar cache de áudios antigos: {str(e)}")

# Exemplo de uso (pode ser removido ou comentado)
if __name__ == "__main__":
    print("Testando módulo audio_processor.py...")
    
    # Teste de geração de áudio do bot
    test_text = "Olá! Este é um teste de áudio do sistema Equinos Seguros."
    audio_file = generate_bot_audio_response(test_text)
    if audio_file:
        print(f"Áudio de teste do bot gerado: {audio_file}")
        print(f"Caminho completo: {os.path.join(BOT_AUDIO_CACHE_DIR, audio_file)}")
        # Tente gerar novamente para testar o cache
        audio_file_cached = generate_bot_audio_response(test_text)
        assert audio_file == audio_file_cached, "Cache não funcionou como esperado."
        print("Teste de cache de áudio do bot bem-sucedido.")
    else:
        print("Falha ao gerar áudio de teste do bot.")

    # Para testar a transcrição, você precisaria de uma URL de áudio válida
    # Exemplo: test_media_url = "URL_DE_UM_ARQUIVO_OGG_PUBLICO"
    # if test_media_url:
    #     transcribed_text = convert_user_audio_to_text(test_media_url)
    #     print(f"Texto transcrito do áudio do usuário: {transcribed_text}")
    # else:
    #     print("URL de mídia de teste não fornecida para transcrição.")

    print("Testes do audio_processor.py concluídos (parcialmente, transcrição requer URL).")

