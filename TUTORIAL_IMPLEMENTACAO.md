# Tutorial de Implementação: Chatbot WhatsApp com Handoff para Agente

Este tutorial guiará você pelo processo de configuração e execução do projeto de chatbot WhatsApp com funcionalidade de handoff para agentes humanos.

## Sumário

1.  [Pré-requisitos](#1-pré-requisitos)
2.  [Estrutura do Projeto](#2-estrutura-do-projeto)
3.  [Configuração do Ambiente](#3-configuração-do-ambiente)
    *   [Clonar o Repositório](#clonar-o-repositório)
    *   [Criar e Configurar o Arquivo `.env`](#criar-e-configurar-o-arquivo-env)
    *   [Criar um Ambiente Virtual Python](#criar-um-ambiente-virtual-python)
    *   [Instalar Dependências](#instalar-dependências)
4.  [Configuração dos Serviços Externos](#4-configuração-dos-serviços-externos)
    *   [MongoDB](#mongodb)
    *   [Twilio](#twilio)
    *   [OpenAI](#openai)
    *   [Ngrok (para desenvolvimento local)](#ngrok-para-desenvolvimento-local)
5.  [Executando a Aplicação](#5-executando-a-aplicação)
    *   [Com Docker Compose (Recomendado)](#com-docker-compose-recomendado)
    *   [Manualmente (Sem Docker)](#manualmente-sem-docker)
6.  [Testando a Aplicação](#6-testando-a-aplicação)
    *   [Configurando o Webhook no Twilio](#configurando-o-webhook-no-twilio)
    *   [Enviando uma Mensagem](#enviando-uma-mensagem)
    *   [Testando o Handoff](#testando-o-handoff)
    *   [Acessando o Painel do Agente](#acessando-o-painel-do-agente)
7.  [Implantação em Produção (Sugestões)](#7-implantação-em-produção-sugestões)
8.  [Considerações Adicionais](#8-considerações-adicionais)

---

## 1. Pré-requisitos

Antes de começar, certifique-se de que você tem os seguintes softwares instalados:

*   **Python 3.8+** e **pip**
*   **Git**
*   **Docker** e **Docker Compose** (Recomendado para facilitar a execução)
*   Uma conta **Twilio** com um número WhatsApp ativado (pode ser o sandbox para testes)
*   Uma chave de API da **OpenAI**
*   Acesso a uma instância **MongoDB** (local ou na nuvem, como MongoDB Atlas)
*   **Ngrok** (ou uma forma de expor sua máquina local publicamente para o webhook do Twilio durante o desenvolvimento)

---

## 2. Estrutura do Projeto

O projeto está organizado da seguinte forma:

```
whatsapp_handoff_project/
├── app/                    # Contém o código principal da aplicação Flask
│   ├── __init__.py         # Inicializa o pacote app e registra blueprints
│   ├── main.py             # Ponto de entrada da aplicação Flask, webhook principal
│   ├── bot/                # Lógica específica do bot
│   │   ├── __init__.py
│   │   └── handler.py      # Processamento de mensagens pelo bot (OpenAI GPT)
│   ├── agent/              # Lógica e interface para agentes humanos
│   │   ├── __init__.py
│   │   ├── routes.py       # Rotas para o painel do agente
│   │   ├── templates/      # Templates HTML para o painel do agente
│   │   │   ├── agent_base.html
│   │   │   ├── agent_login.html
│   │   │   ├── agent_dashboard.html
│   │   │   └── agent_conversation.html
│   │   └── static/         # Arquivos estáticos para o painel do agente (CSS, JS)
│   │       └── css/style.css (Exemplo, crie se necessário)
│   ├── db/                 # Módulo de interação com o banco de dados
│   │   ├── __init__.py
│   │   └── database.py     # Funções para MongoDB
│   ├── utils/              # Utilitários diversos
│   │   ├── __init__.py
│   │   ├── audio_processor.py # Processamento de áudio (Whisper, TTS)
│   │   └── twilio_utils.py # (Opcional) Funções utilitárias para Twilio
│   └── static_bot_audio/   # Cache para áudios gerados pelo bot
├── tests/                  # Testes (a serem implementados)
│   └── __init__.py
├── .env.example            # Exemplo de arquivo de variáveis de ambiente
├── .env                    # Arquivo de variáveis de ambiente (NÃO versionar no Git)
├── Dockerfile              # Para construir a imagem Docker da aplicação
├── docker-compose.yml      # Para orquestrar os contêineres (app e MongoDB)
├── requirements.txt        # Dependências Python do projeto
├── README.md               # Informações gerais sobre o projeto
└── TUTORIAL_IMPLEMENTACAO.md # Este arquivo
```

---

## 3. Configuração do Ambiente

### Clonar o Repositório

Se você recebeu o projeto como um arquivo ZIP, descompacte-o. Se estiver em um repositório Git:

```bash
# git clone <URL_DO_REPOSITORIO>
# cd whatsapp_handoff_project
```

### Criar e Configurar o Arquivo `.env`

Copie o arquivo `.env.example` para um novo arquivo chamado `.env` na raiz do projeto:

```bash
cp .env.example .env
```

Agora, edite o arquivo `.env` com suas credenciais e configurações específicas:

```ini
# /home/ubuntu/whatsapp_handoff_project/.env

# Configurações do Twilio
TWILIO_ACCOUNT_SID="SEU_ACCOUNT_SID_TWILIO"
TWILIO_AUTH_TOKEN="SEU_AUTH_TOKEN_TWILIO"
TWILIO_WHATSAPP_NUMBER="whatsapp:+NUMERO_WHATSAPP_TWILIO" # Ex: whatsapp:+14155238886

# Configurações da OpenAI
OPENAI_API_KEY="SUA_CHAVE_API_OPENAI"

# Configurações do Banco de Dados MongoDB
MONGO_URI="mongodb://localhost:27017/" # Ou sua URI do MongoDB Atlas
DB_NAME="whatsapp_handoff_db"

# Configurações do Flask
FLASK_APP="app.main:app"
FLASK_DEBUG="True" # Mude para "False" em produção
FLASK_SECRET_KEY="gere_uma_chave_secreta_forte_aqui" # Ex: use `openssl rand -hex 32`

# URL Base da Aplicação
BASE_URL="http://localhost:5000" # Será atualizado com Ngrok ou domínio de produção

# Porta para a aplicação Flask
PORT=5000
```

**Importante:**
*   Substitua os valores de exemplo pelas suas credenciais reais.
*   `FLASK_SECRET_KEY`: Gere uma chave secreta forte e única. Você pode usar `python -c 'import secrets; print(secrets.token_hex(24))'` no terminal.
*   `BASE_URL`: Inicialmente `http://localhost:5000`. Quando usar Ngrok, você atualizará esta URL para a URL pública fornecida pelo Ngrok.

### Criar um Ambiente Virtual Python

É uma boa prática usar um ambiente virtual para isolar as dependências do projeto.

```bash
python3 -m venv venv
```

Ative o ambiente virtual:

*   No Linux/macOS:
    ```bash
    source venv/bin/activate
    ```
*   No Windows:
    ```bash
    venv\Scripts\activate
    ```

### Instalar Dependências

Com o ambiente virtual ativado, instale as dependências listadas no `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 4. Configuração dos Serviços Externos

### MongoDB

*   **Localmente (via Docker Compose):** O arquivo `docker-compose.yml` já está configurado para iniciar um contêiner MongoDB. Você não precisa fazer nada extra se for usar Docker Compose.
*   **MongoDB Atlas (Nuvem):**
    1.  Crie uma conta gratuita no [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
    2.  Crie um cluster gratuito.
    3.  Configure o acesso à rede para permitir conexões do seu IP ou de qualquer lugar (`0.0.0.0/0` - menos seguro, use com cautela).
    4.  Crie um usuário de banco de dados com permissões de leitura e escrita.
    5.  Obtenha a string de conexão (URI) e atualize `MONGO_URI` no seu arquivo `.env`.
        *   Exemplo de URI do Atlas: `mongodb+srv://<username>:<password>@<cluster-url>/<dbname>?retryWrites=true&w=majority`

### Twilio

1.  Acesse seu [Console Twilio](https://www.twilio.com/console).
2.  Anote seu `Account SID` e `Auth Token` (disponíveis na página inicial do console).
3.  Configure o [Sandbox do WhatsApp da Twilio](https://www.twilio.com/console/sms/whatsapp/sandbox) ou compre um número Twilio habilitado para WhatsApp.
    *   Para o Sandbox, você precisará enviar uma mensagem específica do seu WhatsApp para o número do sandbox para conectá-lo.
    *   Anote o número do WhatsApp da Twilio (ex: `whatsapp:+14155238886`).
4.  Preencha `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, e `TWILIO_WHATSAPP_NUMBER` no arquivo `.env`.

### OpenAI

1.  Acesse sua [Plataforma OpenAI](https://platform.openai.com/).
2.  Vá para a seção de chaves de API (`API keys`).
3.  Crie uma nova chave secreta.
4.  Copie a chave e preencha `OPENAI_API_KEY` no arquivo `.env`.

### Ngrok (para desenvolvimento local)

O Twilio precisa de uma URL pública para enviar eventos de webhook (novas mensagens). Se você estiver rodando a aplicação localmente, o Ngrok pode criar um túnel seguro para sua máquina.

1.  [Baixe e instale o Ngrok](https://ngrok.com/download).
2.  Autentique o Ngrok (opcional, mas recomendado para mais funcionalidades):
    ```bash
    ngrok config add-authtoken SEU_AUTHTOKEN_NGROK
    ```
3.  Quando sua aplicação Flask estiver rodando (veremos na próxima seção), você iniciará o Ngrok para expor a porta da sua aplicação (geralmente 5000):
    ```bash
    ngrok http 5000
    ```
4.  O Ngrok fornecerá uma URL pública no formato `https://xxxx-xxxx.ngrok-free.app`. Você usará esta URL para configurar o webhook no Twilio e também precisará atualizar a variável `BASE_URL` no seu arquivo `.env` para esta URL Ngrok (incluindo `https://`).

---

## 5. Executando a Aplicação

### Com Docker Compose (Recomendado)

Esta é a maneira mais fácil de iniciar a aplicação e o banco de dados MongoDB juntos.

1.  Certifique-se de que o Docker e Docker Compose estão instalados e rodando.
2.  Na raiz do projeto (onde está o `docker-compose.yml`), execute:
    ```bash
    docker-compose up --build
    ```
    *   O `--build` reconstrói a imagem se houver alterações no `Dockerfile` ou no código.
    *   Para rodar em segundo plano (detached mode), use `docker-compose up -d --build`.

3.  A aplicação Flask estará rodando na porta especificada em `PORT` no `.env` (padrão 5000) dentro do contêiner, e o MongoDB estará acessível.

Para parar os contêineres:

```bash
docker-compose down
```

### Manualmente (Sem Docker)

1.  **Inicie o MongoDB:**
    *   Se você instalou o MongoDB localmente (sem Docker), certifique-se de que o serviço está rodando.
    *   Se estiver usando MongoDB Atlas, ele já está rodando na nuvem.

2.  **Inicie a Aplicação Flask:**
    *   Certifique-se de que seu ambiente virtual Python está ativado (`source venv/bin/activate`).
    *   Certifique-se de que o arquivo `.env` está configurado corretamente.
    *   Na raiz do projeto, execute:
        ```bash
        flask run --host=0.0.0.0 --port=${PORT:-5000}
        ```
        Ou, se você configurou `app.main:app` como `FLASK_APP`:
        ```bash
        python -m flask run --host=0.0.0.0 --port=${PORT:-5000}
        ```
        A aplicação estará rodando em `http://localhost:5000` (ou a porta que você configurou).

---

## 6. Testando a Aplicação

### Configurando o Webhook no Twilio

1.  **Inicie sua aplicação Flask** (localmente ou via Docker).
2.  **Inicie o Ngrok** (se estiver rodando localmente) para obter uma URL pública:
    ```bash
    ngrok http 5000 # Ou a porta que sua aplicação está usando
    ```
    Copie a URL `https://xxxx-xxxx.ngrok-free.app` fornecida pelo Ngrok.
3.  **Atualize `BASE_URL` no seu arquivo `.env`** para esta URL Ngrok (ex: `BASE_URL="https://xxxx-xxxx.ngrok-free.app"`). Se estiver usando Docker Compose, você pode precisar reiniciar os contêineres (`docker-compose down && docker-compose up --build`) para que a aplicação Flask use a nova `BASE_URL` para gerar URLs de áudio corretamente.
4.  **No Console Twilio:**
    *   Vá para a configuração do seu número WhatsApp (ou Sandbox do WhatsApp).
    *   Encontre a seção de "Messaging" ou "Quando uma mensagem chegar" (When a message comes in).
    *   Cole a URL do seu webhook, que será sua URL pública + `/webhook`. Exemplo: `https://xxxx-xxxx.ngrok-free.app/webhook`.
    *   Certifique-se de que o método está configurado para `HTTP POST`.
    *   Salve as configurações.

### Enviando uma Mensagem

Envie uma mensagem de texto ou áudio do seu número de WhatsApp pessoal (que você conectou ao Sandbox da Twilio, se estiver usando) para o seu número WhatsApp da Twilio.

Você deverá ver logs no terminal onde sua aplicação Flask está rodando, indicando que a mensagem foi recebida e processada.

### Testando o Handoff

Envie uma mensagem contendo uma das palavras-chave de handoff, como "falar com atendente" ou "ajuda humana".

*   O bot deve responder algo como "Ok, vou te transferir para um de nossos atendentes."
*   No banco de dados (MongoDB), o status da conversa deve mudar para `AWAITING_AGENT`.

### Acessando o Painel do Agente

1.  Abra seu navegador e acesse a URL do painel do agente. Se estiver rodando localmente, será `http://localhost:5000/agent/login`.
2.  Faça login com as credenciais de agente configuradas (exemplo em `app/agent/routes.py`):
    *   Email: `agent1@equinos.com`
    *   Senha: `agente123`
3.  No dashboard (`/agent/dashboard`), você deve ver a conversa que está `AWAITING_AGENT`.
4.  Clique para visualizar/assumir a conversa.
5.  Assuma a conversa. O status deve mudar para `AGENT_ACTIVE`.
6.  Envie uma mensagem como agente. A mensagem deve aparecer no seu WhatsApp pessoal.
7.  Responda do seu WhatsApp pessoal. A mensagem deve aparecer no histórico da conversa no painel do agente (pode precisar de um refresh manual se não houver WebSockets implementados para tempo real).
8.  Marque a conversa como resolvida.

---

## 7. Implantação em Produção (Sugestões)

Para produção, considere as seguintes plataformas e práticas:

*   **Plataformas de Hospedagem:**
    *   **Render:** Boa para aplicações Python/Flask e contêineres Docker. Oferece bancos de dados gerenciados.
    *   **Heroku (agora parte da Salesforce):** Similar ao Render, com suporte a buildpacks e Docker.
    *   **Servidores VPS (DigitalOcean, Linode, AWS EC2):** Maior controle, mas requer mais configuração manual. Use Docker para facilitar.
    *   **AWS Elastic Beanstalk, Google App Engine:** Plataformas como Serviço (PaaS) que gerenciam muita da infraestrutura.
*   **Banco de Dados:** Use um serviço de banco de dados gerenciado como MongoDB Atlas em produção.
*   **Servidor WSGI:** Use um servidor WSGI robusto como Gunicorn (já incluído no `Dockerfile` e `requirements.txt`) em vez do servidor de desenvolvimento do Flask.
*   **Variáveis de Ambiente:** Configure as variáveis de ambiente diretamente na plataforma de hospedagem, em vez de usar um arquivo `.env` no servidor de produção.
*   **HTTPS:** Certifique-se de que sua aplicação está servida sobre HTTPS. A maioria das plataformas de hospedagem configura isso automaticamente ou facilita a configuração.
*   **Domínio Personalizado:** Configure um domínio personalizado para sua aplicação.
*   **Logging e Monitoramento:** Configure logging centralizado e monitoramento de performance.

---

## 8. Considerações Adicionais

*   **Segurança:**
    *   Mantenha suas chaves de API e segredos seguros. Não os versione no Git.
    *   Use senhas fortes e hasheadas para o login de agentes.
    *   Valide todas as entradas do usuário.
*   **Escalabilidade:** Se você espera um grande volume de mensagens, planeje a escalabilidade da sua aplicação e banco de dados.
*   **Interface do Agente em Tempo Real:** Para uma melhor experiência do agente, considere adicionar WebSockets (ex: usando Flask-SocketIO) para atualizar o painel do agente em tempo real sem a necessidade de recarregar a página.
*   **Notificações para Agentes:** Implemente um sistema de notificação mais robusto para agentes (ex: email, Slack) quando novas conversas precisarem de atenção.

Boa sorte com a implementação! Se tiver dúvidas, consulte a documentação das ferramentas e bibliotecas utilizadas.
