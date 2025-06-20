import os
import openai
from dotenv import load_dotenv
from ..utils.animal_data_collector import AnimalDataCollector
from ..utils.whatsapp_file_manager import send_pdf_to_whatsapp
from ..bot.swissre_melhorado import executar_cotacao_swissre
from ..db import database

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

def get_bot_response(user_message, phone_number, conversation_id):
    """
    Obtém uma resposta do bot para a mensagem do usuário.
    Retorna uma tupla (resposta, is_handoff_request, pdf_path).
    """
    # Verificar se é um pedido de handoff
    is_handoff_request = any(keyword.lower() in user_message.lower() for keyword in HANDOFF_KEYWORDS)
    
    if is_handoff_request:
        return "Entendi que você gostaria de falar com um atendente humano. Estou transferindo sua conversa para um de nossos agentes. Por favor, aguarde um momento.", True, None
    
    # Inicializar coletor de dados do animal
    data_collector = AnimalDataCollector(phone_number)
    
    # Extrair e atualizar dados da mensagem
    updated_fields = data_collector.extract_and_update_data(user_message)
    
    # Salvar dados atualizados
    if updated_fields and conversation_id:
        data_collector.save_data(conversation_id)
    
    # Verificar se todos os dados foram coletados
    if data_collector.is_complete():
        # Todos os dados foram coletados, iniciar processo de cotação
        return processar_cotacao_completa(data_collector, phone_number)
    
    # Ainda faltam dados, gerar resposta do bot
    try:
        # Preparar contexto para o bot
        dados_coletados = data_collector.get_summary()
        campos_faltantes = data_collector.get_missing_fields()
        
        # Criar prompt personalizado baseado no estado atual
        if not data_collector.data:
            # Primeira interação
            system_prompt = """
            Você é um assistente de seguros para equinos da empresa **Equinos Seguros**, especializado em cotação de seguros Pecuário Individual, Rebanhos ou animais de Competição e Exposição.

            Esta é a primeira interação com o cliente. Apresente-se de forma calorosa e explique que você irá coletar as informações necessárias para realizar a cotação do seguro.

            Explique que precisa das seguintes informações obrigatórias:
            - Nome do Animal
            - Valor do Animal
            - Número de Registro ou Passaporte (se tiver)
            - Raça
            - Data de Nascimento
            - Sexo (inteiro, castrado ou fêmea)
            - Utilização (lazer, salto, laço etc.)
            - Endereço da Cocheira (CEP e cidade)

            Peça para o cliente começar fornecendo essas informações. Seja acolhedor e profissional.
            Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas.
            """
        else:
            # Interações subsequentes
            system_prompt = f"""
            Você é um assistente de seguros para equinos da empresa **Equinos Seguros**.

            DADOS JÁ COLETADOS:
            {dados_coletados}

            CAMPOS AINDA FALTANTES:
            {', '.join(campos_faltantes) if campos_faltantes else 'Nenhum'}

            Sua tarefa é:
            1. Agradecer pelas informações fornecidas
            2. Se ainda faltam campos, perguntar especificamente pelos campos faltantes
            3. Ser educado e encorajador
            4. Manter o foco na coleta de dados

            Responda em português do Brasil, de forma clara e objetiva. Limite suas respostas a 3-4 frases curtas.
            """
        
        # Usar a API da OpenAI para gerar uma resposta
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Extrair a resposta do modelo
        bot_response = response.choices[0].message.content.strip()
        
        # Se foram atualizados campos, mencionar isso na resposta
        if updated_fields:
            field_names = [AnimalDataCollector.REQUIRED_FIELDS[field] for field in updated_fields]
            bot_response += f"\n\n✅ Atualizei: {', '.join(field_names)}"
        
        return bot_response, False, None
        
    except Exception as e:
        print(f"Erro ao obter resposta da OpenAI: {e}")
        return "Desculpe, estou com dificuldades para processar sua solicitação no momento. Posso ajudar com algo mais simples ou você prefere falar com um atendente humano?", False, None

def processar_cotacao_completa(data_collector, phone_number):
    """
    Processa a cotação quando todos os dados estão completos.
    """
    try:
        # Obter dados formatados para o SwissRe
        dados_animal = data_collector.get_formatted_data_for_swissre()
        
        # Mostrar resumo final para confirmação
        resumo = data_collector.get_summary()
        resposta_confirmacao = f"""✅ **Perfeito! Coletei todas as informações necessárias.**

{resumo}

🔄 **Iniciando processo de cotação...**

Vou processar sua solicitação no sistema da seguradora. Isso pode levar alguns minutos. 

📄 Assim que a cotação estiver pronta, enviarei o documento PDF com todos os detalhes.

⏳ Por favor, aguarde..."""

        # Executar cotação em background (você pode implementar isso como uma tarefa assíncrona)
        try:
            sucesso, mensagem, pdf_path = executar_cotacao_swissre(dados_animal)
            
            if sucesso and pdf_path:
                # Enviar PDF via WhatsApp
                if send_pdf_to_whatsapp(phone_number, pdf_path, dados_animal):
                    resposta_final = """🎉 **Cotação concluída com sucesso!**

📄 Enviei o documento PDF com sua cotação via WhatsApp.

O arquivo contém:
• Detalhes da cobertura
• Valor do prêmio
• Condições gerais
• Instruções para contratação

💬 Se tiver dúvidas ou desejar prosseguir com a contratação, estou à disposição!

✅ Obrigado por escolher a Equinos Seguros!"""
                else:
                    resposta_final = """✅ **Cotação processada com sucesso!**

❌ Houve um problema técnico no envio do PDF. 

🔄 **Vou tentar reenviar em alguns instantes.**

💬 Se não receber o documento, entre em contato conosco para que possamos enviar por outro meio.

Obrigado pela paciência!"""
            else:
                resposta_final = f"""❌ **Problema no processamento da cotação**

Detalhes: {mensagem}

🔄 **Vou tentar novamente em alguns instantes.**

💬 Se o problema persistir, um de nossos atendentes entrará em contato com você.

Pedimos desculpas pelo inconveniente."""
                
        except Exception as e:
            print(f"Erro ao executar cotação: {e}")
            resposta_final = """❌ **Problema técnico no sistema de cotação**

🔧 Nosso sistema está temporariamente indisponível.

👨‍💼 **Um atendente humano entrará em contato com você em breve** para processar sua cotação manualmente.

📞 Ou você pode ligar para nosso atendimento se preferir.

Pedimos desculpas pelo inconveniente."""
        
        return resposta_confirmacao, False, None
        
    except Exception as e:
        print(f"Erro ao processar cotação completa: {e}")
        return "Ocorreu um erro ao processar sua cotação. Um atendente entrará em contato com você em breve.", False, None

