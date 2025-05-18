# Configuração Segura de Variáveis de Ambiente

Este documento explica como configurar corretamente as variáveis de ambiente para o projeto WhatsApp Handoff, garantindo segurança e evitando o vazamento de credenciais sensíveis.

## Variáveis de Ambiente Necessárias

O projeto requer as seguintes variáveis de ambiente:

1. **OpenAI API**
   - `OPENAI_API_KEY`: Sua chave de API da OpenAI

2. **MongoDB**
   - `MONGO_URI`: URI de conexão com o MongoDB
   - `DB_NAME`: Nome do banco de dados (padrão: "minhacolect")

3. **Twilio (para WhatsApp)**
   - `TWILIO_ACCOUNT_SID`: ID da conta Twilio
   - `TWILIO_AUTH_TOKEN`: Token de autenticação Twilio
   - `TWILIO_WHATSAPP_NUMBER`: Número do WhatsApp no formato "whatsapp:+XXXXXXXXXX"

4. **Flask**
   - `FLASK_APP`: Ponto de entrada da aplicação (padrão: "app:create_app()")
   - `FLASK_DEBUG`: Modo de depuração (padrão: "False" em produção)
   - `FLASK_SECRET_KEY`: Chave secreta para sessões e cookies

## Configuração no Ambiente de Desenvolvimento

Para desenvolvimento local, você pode usar um arquivo `.env`:

1. Copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edite o arquivo `.env` e adicione suas credenciais reais.

3. **IMPORTANTE**: Nunca comite o arquivo `.env` para o repositório Git. Ele já está incluído no `.gitignore`.

## Configuração no Render (Produção)

Para o ambiente de produção no Render, configure as variáveis de ambiente diretamente no painel do Render:

1. Acesse o dashboard do Render
2. Selecione seu serviço web
3. Vá para a aba "Environment"
4. Adicione cada variável de ambiente necessária:
   - Clique em "Add Environment Variable"
   - Digite o nome da variável (ex: "OPENAI_API_KEY")
   - Digite o valor da variável (sua chave real)
   - Repita para todas as variáveis necessárias

## Evitando Erros de Segurança no GitHub

O GitHub bloqueia pushes que contenham credenciais sensíveis. Para evitar esse problema:

1. **Nunca comite arquivos com credenciais reais**
2. Use apenas o arquivo `.env.example` com placeholders no repositório
3. Mantenha o arquivo `.env` no `.gitignore`
4. Configure as credenciais reais apenas no ambiente de produção (Render)

Se você receber um erro do GitHub sobre "Push cannot contain secrets", verifique se não há credenciais reais em nenhum arquivo do seu repositório.

## Verificação de Segurança

Antes de fazer push para o GitHub, você pode verificar se há credenciais sensíveis no seu código:

```bash
git diff --staged | grep -E '(key|token|password|secret|sid)'
```

Este comando mostrará qualquer linha que possa conter credenciais sensíveis.

## Recuperação de Credenciais no Código

No código, as credenciais são acessadas usando `os.getenv()`:

```python
import os

# Exemplo de uso
openai_key = os.getenv("OPENAI_API_KEY")
mongo_uri = os.getenv("MONGO_URI")
```

Isso funciona tanto com o arquivo `.env` (em desenvolvimento) quanto com as variáveis de ambiente configuradas no Render (em produção).
