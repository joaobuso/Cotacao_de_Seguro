import os
from twilio.rest import Client

def send_whatsapp_message(to_number, message_text):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        print("ERRO: Credenciais do Twilio não configuradas nas variáveis de ambiente.")
        return False

    # Garantir que os números estão no formato WhatsApp
    if not to_number.startswith('whatsapp:'):
        to_number = f'whatsapp:{to_number}'
    if not from_number.startswith('whatsapp:'):
        from_number = f'whatsapp:{from_number}'
    
    try:
        client = Client(account_sid, auth_token)
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
