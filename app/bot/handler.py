import os
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Configurar a API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Palavras-chave que podem indicar um pedido de handoff
HANDOFF_KEYWORDS = [
    "atendente", "humano", "pessoa", "agente", "falar com alguém", 
    "falar com uma pessoa", "suporte", "ajuda humana", "operador"
]

def get_bot_response(user_message):
    """
    Obtém uma resposta do bot para a mensagem do usuário.
    Retorna uma tupla (resposta, is_handoff_request).
    """
    # Verificar se é um pedido de handoff
    is_handoff_request = any(keyword.lower() in user_message.lower() for keyword in HANDOFF_KEYWORDS)
    
    if is_handoff_request:
        return "Entendi que você gostaria de falar com um atendente humano. Estou transferindo sua conversa para um de nossos agentes. Por favor, aguarde um momento.", True
    
    try:
        # Usar a API da OpenAI para gerar uma resposta
        # Usando a versão mais recente da API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente de seguros para cavalos, especializado em cotações. Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Extrair a resposta do modelo
        bot_response = response.choices[0].message.content.strip()
        return bot_response, False
        
    except Exception as e:
        print(f"Erro ao obter resposta da OpenAI: {e}")
        return "Desculpe, estou com dificuldades para processar sua solicitação no momento. Posso ajudar com algo mais simples ou você prefere falar com um atendente humano?", False
