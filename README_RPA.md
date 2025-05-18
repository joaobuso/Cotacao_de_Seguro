# Chatbot WhatsApp com Handoff para Agente Humano

Este projeto implementa um chatbot para WhatsApp que utiliza a API da OpenAI (GPT) para interações iniciais e oferece um mecanismo de handoff para um agente humano quando necessário. Inclui uma interface web simples para que os agentes possam visualizar e responder às conversas.

## Funcionalidades Principais

*   **Integração com WhatsApp via Twilio:** Recebe e envia mensagens do WhatsApp.
*   **Processamento de Mensagens de Texto e Áudio:**
    *   Converte mensagens de áudio do usuário para texto usando OpenAI Whisper.
    *   Gera respostas de áudio para o bot usando OpenAI TTS.
*   **Inteligência Artificial com OpenAI GPT:** Gera respostas contextuais e personalizadas (configurado para cotação de seguros Equinos Seguros).
*   **Handoff para Agente Humano:**
    *   Permite que o usuário solicite um atendente humano através de palavras-chave.
    *   Altera o status da conversa para `AWAITING_AGENT`.
    *   (Futuro) Notifica os agentes sobre novas solicitações.
*   **Painel do Agente (Interface Web Flask):
    *   Login seguro para agentes.
    *   Dashboard para visualizar conversas aguardando atendimento e conversas ativas.
    *   Visualização do histórico completo da conversa.
    *   Capacidade do agente de assumir uma conversa, enviar mensagens para o usuário via WhatsApp e marcar a conversa como resolvida.
*   **Armazenamento de Histórico de Conversas:** Utiliza MongoDB para persistir todas as mensagens e o status das conversas.
*   **Configuração Flexível:** Utiliza variáveis de ambiente (arquivo `.env`) para configurações sensíveis e específicas da implantação.
*   **Pronto para Docker:** Inclui `Dockerfile` e `docker-compose.yml` para fácil configuração e implantação em contêineres.

## Estrutura do Projeto

Consulte o `TUTORIAL_IMPLEMENTACAO.md` para uma descrição detalhada da estrutura de pastas.

## Tecnologias Utilizadas

*   **Backend:** Python, Flask
*   **WhatsApp API:** Twilio
*   **Inteligência Artificial:** OpenAI (GPT para chat, Whisper para transcrição, TTS para áudio)
*   **Banco de Dados:** MongoDB
*   **Frontend (Painel do Agente):** HTML, Bootstrap (via CDN), Jinja2 (templates Flask)
*   **Containerização:** Docker, Docker Compose

## Como Começar

Siga as instruções detalhadas no arquivo `TUTORIAL_IMPLEMENTACAO.md` para configurar, executar e testar o projeto.

## Pré-requisitos

*   Python 3.8+
*   Git
*   Docker & Docker Compose
*   Conta Twilio
*   Chave API OpenAI
*   Instância MongoDB
*   Ngrok (para desenvolvimento local)

## Configuração

1.  Clone o repositório (ou descompacte os arquivos).
2.  Copie `.env.example` para `.env` e preencha com suas credenciais e URLs.
3.  Crie um ambiente virtual Python e instale as dependências de `requirements.txt`.
4.  Configure seus serviços externos (Twilio, OpenAI, MongoDB).

Consulte o `TUTORIAL_IMPLEMENTACAO.md` para o passo a passo completo.

## Executando a Aplicação

**Com Docker Compose (Recomendado):**

```bash
docker-compose up --build
```

**Manualmente (Flask Development Server):**

```bash
# Ative seu ambiente virtual
# source venv/bin/activate
flask run --host=0.0.0.0 --port=${PORT:-5000}
```

## Acessando o Painel do Agente

Após iniciar a aplicação, o painel do agente estará acessível em `http://localhost:PORTA_CONFIGURADA/agent/login` (ex: `http://localhost:5000/agent/login`).

*   **Credenciais de Exemplo (configuradas em `app/agent/routes.py`):**
    *   Email: `agent1@equinos.com`
    *   Senha: `agente123`

## Contribuições

Este projeto é um ponto de partida. Sinta-se à vontade para expandir e melhorar!

## Licença

(Defina uma licença se desejar, ex: MIT)

