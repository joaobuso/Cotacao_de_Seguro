# Acesso ao Painel do Agente - Guia Detalhado

Este documento explica como acessar e utilizar o painel do agente para gerenciar as conversas entre usuários e o chatbot WhatsApp.

## Como Acessar o Painel

Após a implantação bem-sucedida no Render, o painel do agente estará disponível em:

```
https://seu-app-name.onrender.com/agent/login
```

Substitua `seu-app-name` pelo nome que você deu ao seu serviço no Render.

## Credenciais de Acesso

As credenciais padrão para acessar o painel do agente são:

- **Email**: agent1@equinos.com
- **Senha**: agente123

**IMPORTANTE**: Por segurança, recomendamos alterar essas credenciais antes de usar em produção. Você pode editar o arquivo `app/agent/routes.py` para modificar o dicionário `AGENTS_DB`.

## Funcionalidades do Painel

### 1. Dashboard Principal

Após fazer login, você verá o dashboard principal com duas seções:

- **Conversas Aguardando Atendimento**: Conversas que foram transferidas do bot para um agente humano
- **Minhas Conversas Ativas**: Conversas que você assumiu e estão em andamento

### 2. Visualizar uma Conversa

Clique no botão "Ver / Assumir" ao lado de uma conversa para visualizar o histórico completo de mensagens entre o usuário e o bot.

### 3. Assumir uma Conversa

Quando visualizar uma conversa que está aguardando atendimento, clique no botão "Assumir Conversa" para começar a atender o usuário. Isso mudará o status da conversa para "AGENT_ACTIVE".

### 4. Enviar Mensagens

Após assumir uma conversa, você verá um campo de texto na parte inferior da tela. Digite sua mensagem e clique em "Enviar Mensagem" para responder ao usuário via WhatsApp.

### 5. Marcar como Resolvida

Quando o atendimento for concluído, clique no botão "Marcar como Resolvida" para finalizar a conversa. Isso mudará o status para "RESOLVED".

## Fluxo de Trabalho Típico

1. Faça login no painel do agente
2. Verifique se há conversas aguardando atendimento
3. Clique em "Ver / Assumir" para visualizar uma conversa
4. Clique em "Assumir Conversa" para começar a atender
5. Envie mensagens para o usuário conforme necessário
6. Quando o atendimento for concluído, marque a conversa como resolvida
7. Volte ao dashboard para atender outras conversas

## Dicas e Boas Práticas

- **Tempo de Resposta**: Procure responder às conversas aguardando atendimento o mais rápido possível
- **Contexto**: Leia todo o histórico da conversa antes de responder para entender o contexto
- **Personalização**: Use o nome do usuário quando disponível para personalizar o atendimento
- **Resolução**: Só marque uma conversa como resolvida quando tiver certeza de que o problema foi solucionado
- **Monitoramento**: Verifique regularmente o painel para novas conversas aguardando atendimento

## Solução de Problemas

- **Mensagem não enviada**: Verifique se as credenciais do Twilio estão configuradas corretamente
- **Erro ao assumir conversa**: Verifique a conexão com o banco de dados MongoDB
- **Sessão expirada**: Faça login novamente se sua sessão expirar

Para problemas técnicos mais complexos, consulte os logs da aplicação no painel do Render.
