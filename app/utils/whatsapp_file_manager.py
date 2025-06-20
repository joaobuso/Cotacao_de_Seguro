import os
import requests
from twilio.rest import Client
from dotenv import load_dotenv

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(dotenv_path=dotenv_path)

class WhatsAppFileManager:
    """
    Classe para gerenciar envio de arquivos via WhatsApp usando Twilio.
    """
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        self.base_url = os.getenv("BASE_URL", "http://localhost:5000")
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Credenciais do Twilio não configuradas corretamente")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def upload_file_to_server(self, file_path, filename=None):
        """
        Faz upload de um arquivo para o servidor e retorna a URL pública.
        
        Args:
            file_path (str): Caminho local do arquivo
            filename (str): Nome do arquivo (opcional)
            
        Returns:
            str: URL pública do arquivo ou None se houver erro
        """
        try:
            if not os.path.exists(file_path):
                print(f"Arquivo não encontrado: {file_path}")
                return None
            
            # Criar diretório para arquivos públicos se não existir
            public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_files")
            os.makedirs(public_dir, exist_ok=True)
            
            # Definir nome do arquivo
            if not filename:
                filename = os.path.basename(file_path)
            
            # Copiar arquivo para diretório público
            import shutil
            public_file_path = os.path.join(public_dir, filename)
            shutil.copy2(file_path, public_file_path)
            
            # Gerar URL pública
            public_url = f"{self.base_url}/static_files/{filename}"
            
            # Se estiver usando HTTPS, garantir que a URL seja HTTPS
            if self.base_url.startswith("https"):
                public_url = public_url.replace("http://", "https://", 1)
            
            print(f"Arquivo disponibilizado em: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"Erro ao fazer upload do arquivo: {e}")
            return None
    
    def send_document_whatsapp(self, to_number, document_url, caption=None):
        """
        Envia um documento via WhatsApp.
        
        Args:
            to_number (str): Número do destinatário (formato: whatsapp:+5511999999999)
            document_url (str): URL pública do documento
            caption (str): Legenda do documento (opcional)
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Garantir que o número esteja no formato correto
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Enviar documento
            message = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_number,
                media_url=[document_url],
                body=caption or "Documento anexado"
            )
            
            print(f"Documento enviado com sucesso. SID: {message.sid}")
            return True
            
        except Exception as e:
            print(f"Erro ao enviar documento via WhatsApp: {e}")
            return False
    
    def send_pdf_cotacao(self, to_number, pdf_path, dados_animal):
        """
        Envia PDF de cotação via WhatsApp com mensagem personalizada.
        
        Args:
            to_number (str): Número do destinatário
            pdf_path (str): Caminho do arquivo PDF
            dados_animal (dict): Dados do animal para personalizar a mensagem
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Fazer upload do PDF
            pdf_url = self.upload_file_to_server(pdf_path)
            if not pdf_url:
                return False
            
            # Criar mensagem personalizada
            nome_animal = dados_animal.get('nome_animal', 'Animal')
            caption = f"""🐎 **Cotação de Seguro - {nome_animal}**

📋 Sua cotação foi processada com sucesso!

📄 O documento em anexo contém todos os detalhes da cotação, incluindo:
• Cobertura oferecida
• Valor do prêmio
• Condições gerais
• Instruções para contratação

💬 Se tiver dúvidas ou desejar prosseguir com a contratação, entre em contato conosco.

✅ Obrigado por escolher nossos serviços!"""
            
            # Enviar PDF
            return self.send_document_whatsapp(to_number, pdf_url, caption)
            
        except Exception as e:
            print(f"Erro ao enviar PDF de cotação: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours=24):
        """
        Remove arquivos antigos do diretório público.
        
        Args:
            max_age_hours (int): Idade máxima dos arquivos em horas
        """
        try:
            from datetime import datetime
            
            public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_files")
            if not os.path.exists(public_dir):
                return
            
            current_time = datetime.now()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(public_dir):
                file_path = os.path.join(public_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time.timestamp() - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        print(f"Arquivo antigo removido: {filename}")
                        
        except Exception as e:
            print(f"Erro ao limpar arquivos antigos: {e}")

def send_pdf_to_whatsapp(phone_number, pdf_path, dados_animal):
    """
    Função utilitária para enviar PDF via WhatsApp.
    
    Args:
        phone_number (str): Número do telefone
        pdf_path (str): Caminho do arquivo PDF
        dados_animal (dict): Dados do animal
        
    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    try:
        file_manager = WhatsAppFileManager()
        return file_manager.send_pdf_cotacao(phone_number, pdf_path, dados_animal)
    except Exception as e:
        print(f"Erro ao enviar PDF: {e}")
        return False

