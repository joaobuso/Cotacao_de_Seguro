import os
from twilio.rest import Client

# Função para enviar mensagem via WhatsApp usando a API do Twilio
def send_whatsapp_message(to_number, message_text):
    """
    Envia uma mensagem de WhatsApp para o número especificado usando a API do Twilio.
    
    Args:
        to_number (str): Número de telefone do destinatário no formato whatsapp:+XXXXXXXXXXX
        message_text (str): Texto da mensagem a ser enviada
        
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    # Obter credenciais do Twilio das variáveis de ambiente
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
    
    # Verificar se as credenciais estão configuradas
    if not account_sid or not auth_token or not from_number:
        print("ERRO: Credenciais do Twilio não configuradas nas variáveis de ambiente.")
        return False
    
    try:
        # Inicializar cliente Twilio
        client = Client(account_sid, auth_token)
        
        # Garantir que o número de destino está no formato correto para WhatsApp
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        # Enviar mensagem
        message = client.messages.create(
            body=message_text,
            from_=from_number,
            to=to_number
        )
        
        print(f"Mensagem enviada com sucesso! SID: {message.sid}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar mensagem via Twilio: {str(e)}")
        return False
