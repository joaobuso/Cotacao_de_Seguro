# /home/ubuntu/whatsapp_handoff_project/app/bot/handler.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("AVISO: OPENAI_API_KEY não configurada no .env para o bot handler.")


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Palavras-chave para acionar o handoff para um agente humano
HANDOFF_KEYWORDS = [
    "falar com atendente",
    "falar com humano",
    "atendente",
    "humano",
    "suporte",
    "ajuda humana"
]

# Prompt do sistema para o GPT
# As informações obrigatórias foram mantidas conforme o código original do usuário.
SYSTEM_PROMPT = """
Você é o corretor virtual da empresa **Equinos Seguros**, especializado em cotação de seguros Pecuário Individual, Rebanhos ou animais de Competição e Exposição.

Sua função é orientar o cliente a fornecer todas as informações obrigatórias para realizar a cotação. Se o cliente pedir para falar com um atendente ou usar palavras como 'humano', 'suporte', 'atendente', responda apenas com a frase 'Ok, vou te transferir para um de nossos atendentes.' e mais nada.

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

Quando todas as informações forem enviadas, avise ao usuário que os resultados serão entregues em dois documentos (links de exemplo):
link_swissre = https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing
link_fairfax = https://drive.google.com/file/d/1duauc3jLLkpi-7eTN3TJLi2RypTA4_Qk/view?usp=sharing

Exemplo de resposta final quando todos os dados forem coletados:
'Obrigado por fornecer todas as informações necessárias para a cotação do seguro do animal [Nome do Animal].

Os resultados da cotação serão entregues em dois documentos, disponíveis nos links abaixo:

- Cotação Seguradora SwissRe: {link_swissre}
- Cotação Seguradora Fairfax: {link_fairfax}

Se precisar de mais alguma assistência ou informações, estou à disposição ou posso te transferir para um de nossos atendentes.'

Comunique-se de forma clara, acolhedora e profissional, sempre em português do Brasil.
Responda de maneira educada, perguntando dados adicionais sempre que necessário.
"""

def check_for_handoff_request(user_message):
    """Verifica se a mensagem do usuário contém palavras-chave para handoff."""
    for keyword in HANDOFF_KEYWORDS:
        if keyword in user_message.lower():
            return True
    return False

def get_bot_response(user_message, conversation_history=None):
    """Obtém uma resposta do bot usando OpenAI GPT.
       conversation_history é uma lista de mensagens anteriores no formato OpenAI.
       Ex: [{"role": "user", "content": "Olá"}, {"role": "assistant", "content": "Olá! Como posso ajudar?"}]
    """
    if not OPENAI_API_KEY:
        return "Desculpe, o serviço de inteligência artificial não está configurado no momento.", False

    is_handoff = check_for_handoff_request(user_message)
    if is_handoff:
        return "Ok, vou te transferir para um de nossos atendentes.", True

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    if conversation_history:
        messages.extend(conversation_history) # Adiciona histórico se houver
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # ou "gpt-4" se disponível e preferido
            messages=messages
        )
        reply = response.choices[0].message.content
        return reply, False # False indica que não é um pedido de handoff direto
    except Exception as e:
        print(f"Erro ao obter resposta do OpenAI: {str(e)}")
        return "Desculpe, estou com dificuldades para processar sua solicitação no momento. Tente novamente em alguns instantes.", False

# Exemplo de uso (pode ser removido ou comentado)
if __name__ == "__main__":
    print("Testando módulo bot_handler.py...")
    
    # Teste 1: Mensagem normal
    response1, handoff1 = get_bot_response("Olá, gostaria de fazer uma cotação para meu cavalo.")
    print(f"Usuário: Olá, gostaria de fazer uma cotação para meu cavalo.")
    print(f"Bot: {response1} (Handoff: {handoff1})")
    assert not handoff1

    # Teste 2: Pedido de handoff
    response2, handoff2 = get_bot_response("Preciso falar com um atendente, por favor.")
    print(f"Usuário: Preciso falar com um atendente, por favor.")
    print(f"Bot: {response2} (Handoff: {handoff2})")
    assert handoff2
    assert response2 == "Ok, vou te transferir para um de nossos atendentes."

    # Teste 3: Mensagem com histórico
    history = [
        {"role": "user", "content": "Qual o valor do seguro para um animal de R$50.000?"},
        {"role": "assistant", "content": "Para calcular o valor do seguro, preciso de mais algumas informações. Qual o nome do animal?"}
    ]
    response3, handoff3 = get_bot_response("O nome é Trovão.", conversation_history=history)
    print(f"Usuário: O nome é Trovão.")
    print(f"Bot: {response3} (Handoff: {handoff3})")
    assert not handoff3

    print("Testes do bot_handler.py concluídos.")

