# RPA Cotação de Seguro - Nova Versão 5.0

Bot de cotação de seguros para equinos via WhatsApp com portal de agentes moderno.

## Novidades da Versão 5.0

- **Nova conversação** com menu de 3 opções + FAQ inteligente com 21 temas
- **Front-end React/TypeScript** moderno com TailwindCSS (inspirado no Robo_Exemplo)
- **API REST** completa para o portal de agentes
- **Extração de dados por IA** (OpenAI GPT-4.1-mini) sem campo de e-mail
- **Base de conhecimento FAQ** com 21 temas e busca por palavras-chave

## Estrutura do Projeto

```
RPA_Cotacao_de_Seguro_NOVO/
├── main.py                          # Servidor Flask principal + API REST
├── requirements.txt                 # Dependências Python
├── Dockerfile                       # Container Docker
├── .env                             # Variáveis de ambiente
├── database_manager.py              # Gerenciador de banco em memória
├── database_adapter.py              # Adaptador para banco de dados
├── ultramsg_adapter.py              # Adaptador UltraMsg
├── response_generator.py            # Gerador de respostas
├── templates_portal.py              # Templates legados (compatibilidade)
├── app/
│   ├── bot/
│   │   ├── conversation_flow.py     # NOVO - Fluxo de conversação com FAQ
│   │   ├── bot_handler.py           # NOVO - Handler principal do bot
│   │   ├── data_extractor.py        # NOVO - Extrator de dados com IA (sem e-mail)
│   │   ├── faq_knowledge.py         # NOVO - Base de 21 temas FAQ
│   │   ├── swissre_automation.py    # Automação SwissRe (mantido)
│   │   ├── dados_estados.py         # Dados dos estados (mantido)
│   │   └── pdf_storage.py           # Storage de PDFs (mantido)
│   ├── db/
│   │   └── database.py              # Configuração do banco
│   └── integrations/
│       └── ultramsg_api.py          # API UltraMsg
└── web/
    └── client/                      # Front-end React
        ├── src/
        │   ├── App.tsx              # Roteamento principal
        │   ├── main.tsx             # Entry point
        │   ├── contexts/
        │   │   └── AuthContext.tsx   # Autenticação
        │   ├── components/
        │   │   ├── Layout.tsx       # Layout com sidebar
        │   │   └── Sidebar.tsx      # Navegação lateral
        │   └── pages/
        │       ├── Login.tsx        # Página de login
        │       ├── Dashboard.tsx    # Dashboard com estatísticas
        │       ├── Conversations.tsx # Lista de conversas
        │       ├── ConversationDetail.tsx # Chat com cliente
        │       ├── Quotations.tsx   # Histórico de cotações
        │       └── FaqManager.tsx   # Visualização dos 21 temas FAQ
        └── dist/                    # Build de produção
```

## Fluxo de Conversação

### Menu Principal
1. **Cotação de seguro para cavalo** → Inicia coleta de dados
2. **Como funciona o seguro** → FAQ sobre cotação e contratação
3. **Qual valor do seguro** → FAQ sobre preço e valor

### FAQ Inteligente
O bot reconhece automaticamente 21 temas por palavras-chave:
- Sobre a empresa, SUSEP, localização
- Cotação, preço, vigência
- Coberturas (vida, reprodutiva, esportiva, prenhez, etc.)
- Roubo/furto, sinistro, transporte
- E mais...

### Dados para Cotação (sem e-mail)
- Nome do Solicitante
- Nome do Animal
- Valor do Animal (R$)
- Raça
- Data de Nascimento
- Sexo (inteiro/castrado/fêmea)
- Utilização
- UF (Estado)

## Instalação

### Backend
```bash
pip install -r requirements.txt
python main.py
```

### Front-end (desenvolvimento)
```bash
cd web/client
pnpm install
pnpm dev
```

### Front-end (produção)
```bash
cd web/client
pnpm build
```

## Variáveis de Ambiente

```env
ULTRAMSG_INSTANCE_ID=instance135696
ULTRAMSG_TOKEN=seu_token
OPENAI_API_KEY=sua_chave
MONGO_URI=mongodb+srv://...
DB_NAME=equinos_seguros
FLASK_SECRET_KEY=sua_chave_secreta
CLIENT_ID=client_id_swissre
CLIENT_SECRET=client_secret_swissre
CPF=cpf_padrao
AGENTS=email:senha:Nome,email2:senha2:Nome2
```

## Portal de Agentes

Acesse `/portal` para o portal React moderno com:
- **Dashboard** com estatísticas em tempo real
- **Conversas** com chat ao vivo e mensagens rápidas
- **Cotações** com histórico completo
- **FAQ** com visualização dos 21 temas

## Deploy

### Render
O projeto inclui `render.yaml` e `Dockerfile` prontos para deploy no Render.

### Docker
```bash
docker build -t rpa-cotacao-seguro .
docker run -p 10000:10000 --env-file .env rpa-cotacao-seguro
```
