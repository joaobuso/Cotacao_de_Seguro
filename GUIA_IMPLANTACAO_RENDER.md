# Guia de Implantação no Render e Acesso ao Painel do Agente

## Introdução

Este documento explica como implantar o chatbot WhatsApp com funcionalidade de handoff no Render e como acessar o painel do agente para gerenciar as conversas. O código foi calibrado especificamente para funcionar no Render, com todas as configurações necessárias já preparadas.

## 1. Implantação no Render

### Opção 1: Implantação via Dashboard do Render

1. Crie uma conta no [Render](https://render.com/) se ainda não tiver uma
2. No Dashboard do Render, clique em "New +" e selecione "Web Service"
3. Conecte seu repositório GitHub ou faça upload do código
4. Configure o serviço:
   - **Nome**: whatsapp-handoff-bot (ou outro nome de sua preferência)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT`
5. Configure as variáveis de ambiente:
   - `OPENAI_API_KEY`: Sua chave da OpenAI (já fornecida)
   - `MONGO_URI`: Sua URI do MongoDB (já fornecida, substitua `<db_password>` pela senha real)
   - `DB_NAME`: minhacolect
   - `FLASK_APP`: app:create_app()
   - `FLASK_SECRET_KEY`: Uma chave secreta forte (gerada automaticamente pelo Render)
   - `FLASK_DEBUG`: False
   - Quando estiver pronto para usar o Twilio, adicione:
     - `TWILIO_ACCOUNT_SID`
     - `TWILIO_AUTH_TOKEN`
     - `TWILIO_WHATSAPP_NUMBER`

### Opção 2: Implantação via render.yaml (Mais Simples)

1. Faça login no Render
2. Acesse: https://render.com/deploy
3. Conecte seu repositório GitHub que contém o arquivo `render.yaml`
4. O Render detectará automaticamente o arquivo e configurará o serviço
5. Preencha as variáveis de ambiente solicitadas (OPENAI_API_KEY, MONGO_URI, etc.)
6. Clique em "Apply" para iniciar a implantação

## 2. Acesso ao Painel do Agente

### Como Acessar o Painel

Após a implantação bem-sucedida no Render, o painel do agente estará disponível em:

```
https://seu-app-name.onrender.com/agent/login
```

Substitua `seu-app-name` pelo nome que você deu ao seu serviço no Render.

### Credenciais de Acesso

As credenciais padrão para acessar o painel do agente são:

- **Email**: agent1@equinos.com
- **Senha**: agente123

**IMPORTANTE**: Por segurança, recomendamos alterar essas credenciais antes de usar em produção. Você pode editar o arquivo `app/agent/routes.py` para modificar o dicionário `AGENTS_DB`.

### Funcionalidades do Painel do Agente

O painel do agente permite:

1. **Visualizar conversas pendentes**: Conversas que foram transferidas do bot para um agente humano
2. **Assumir conversas**: Tomar controle de uma conversa para responder ao usuário
3. **Enviar mensagens**: Responder aos usuários via WhatsApp
4. **Visualizar histórico**: Ver todo o histórico de mensagens de uma conversa
5. **Marcar como resolvida**: Finalizar uma conversa quando o atendimento for concluído

## 3. Fluxo de Handoff (Bot para Humano)

O sistema funciona da seguinte forma:

1. O usuário inicia uma conversa com o bot via WhatsApp
2. O bot responde automaticamente usando a OpenAI
3. Se o usuário digitar uma das palavras-chave de handoff (como "falar com atendente", "humano", "suporte"), o bot transfere a conversa para um agente humano
4. A conversa aparece no painel do agente como "Aguardando Atendimento"
5. Um agente humano faz login no painel, visualiza a conversa e a assume
6. O agente responde ao usuário através do painel, e as mensagens são enviadas via WhatsApp
7. Quando o atendimento é concluído, o agente marca a conversa como resolvida

## 4. Configuração do Twilio (Quando Estiver Pronto)

Para ativar o envio de mensagens pelo agente humano, você precisará:

1. Descomentar as variáveis do Twilio no arquivo `.env` ou no painel do Render
2. Configurar o webhook do Twilio para apontar para:
   ```
   https://seu-app-name.onrender.com/webhook
   ```
3. Garantir que seu número do WhatsApp no Twilio esteja ativo e aprovado

## 5. Segurança e Manutenção

- **Credenciais**: Nunca compartilhe suas chaves de API ou senhas
- **Monitoramento**: Verifique regularmente os logs no Render para identificar problemas
- **Backup**: Faça backup regular do banco de dados MongoDB
- **Atualizações**: Mantenha as dependências atualizadas para evitar vulnerabilidades

## Conclusão

Seu chatbot WhatsApp com funcionalidade de handoff está pronto para uso no Render. O sistema permite uma transição suave entre o atendimento automatizado (bot) e o atendimento humano, proporcionando uma experiência completa para seus usuários.

Para qualquer dúvida ou problema, consulte a documentação completa ou entre em contato com o suporte.
