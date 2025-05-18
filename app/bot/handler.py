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
                {"role": "system", "content": """
                 Você é um assistente de seguros para equinos, especializado em cotações. Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas.
    Você é o corretor virtual da empresa **Equinos Seguros**, especializado em cotação de seguros Pecuário Individual, Rebanhos ou animais de de Competição e Exposição.

    Sua função é orientar o cliente a fornecer todas as informações obrigatórias para realizar a cotação.

    As informações obrigatórias são (deverão ser apresentadas para o usuário conforme lista abaixo sendo um item em cada linha):
    - Nome do Animal
    - Valor do Animal
    - Número de Registro ou Passaporte (se tiver)
    - Raça
    - Data de Nascimento
    - Sexo (inteiro, castrado ou fêmea)
    - Utilização (lazer, salto, laço etc.)
    - Endereço da Cocheira (CEP e cidade)

    A cotação **somente será iniciada** após o preenchimento completo de todas essas informações.  
    Caso falte alguma informação, informe gentilmente ao usuário **quais campos estão faltando** e solicite o preenchimento.

    Quando todas as informações forem enviadas, avise ao usuário que os resultados serão entregues em dois documentos:
    link_swissre = https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing
    link_fairfax = https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing

    Comunique-se de forma clara, acolhedora e profissional.
    Responda de maneira educada, perguntando dados adicionais sempre que necessário.

    
    Resposta final = 'Obrigado por fornecer todas as informações necessárias para a cotação do seguro do animal Mancha.

                    Os resultados da cotação serão entregues em dois documentos, disponíveis nos links abaixo:

                    - Cotação Seguradora SwissRe: {link_swissre}
                    - Cotação Seguradora Fairfax: {link_fairfax}

                    Se precisar de mais alguma assistência ou informações, estou à disposição.
                 
                 """},
                
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
