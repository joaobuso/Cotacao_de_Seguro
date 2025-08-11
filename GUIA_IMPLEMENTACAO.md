# 📋 Guia de Implementação Completo

## 🎯 Objetivo
Este guia detalha como implementar o bot de cotação de seguros do zero, passo a passo.

## 📋 Pré-requisitos

### **Contas Necessárias**
- [ ] Conta GitHub (gratuita)
- [ ] Conta UltraMsg (gratuita)
- [ ] Conta OpenAI (paga)
- [ ] Conta MongoDB Atlas (gratuita)
- [ ] Conta Render (gratuita)
- [ ] Conta Cloudinary (opcional, gratuita)

### **Ferramentas**
- [ ] Git instalado
- [ ] Editor de código (VS Code recomendado)
- [ ] WhatsApp Business no celular

---

## 🚀 Passo 1: Configurar UltraMsg

### **1.1 Criar Conta**
1. Acesse https://user.ultramsg.com/
2. Clique em "Sign Up"
3. Preencha: Nome, Email, Senha
4. Confirme o email recebido

### **1.2 Conectar WhatsApp**
1. No dashboard, clique "Connect WhatsApp"
2. **IMPORTANTE:** Use WhatsApp Business (não o comum)
3. Escaneie o QR Code rapidamente (30 segundos)
4. Aguarde confirmação "Connected"

### **1.3 Obter Credenciais**
1. Vá em "API Settings"
2. Copie **Instance ID** (ex: instance135696)
3. Copie **Token** (ex: qtnijalhyl2zhydy)
4. **Guarde essas informações!**

---

## 🧠 Passo 2: Configurar OpenAI

### **2.1 Criar Conta**
1. Acesse https://platform.openai.com/
2. Faça login ou crie conta
3. Adicione método de pagamento

### **2.2 Gerar API Key**
1. Vá em "API Keys"
2. Clique "Create new secret key"
3. Copie a chave (ex: sk-...)
4. **Guarde com segurança!**

### **2.3 Configurar Limites**
1. Vá em "Usage limits"
2. Configure limite mensal (ex: $10)
3. Ative alertas de uso

---

## 🗄️ Passo 3: Configurar MongoDB

### **3.1 Criar Conta Atlas**
1. Acesse https://cloud.mongodb.com/
2. Crie conta gratuita
3. Escolha plano "M0 Sandbox" (gratuito)

### **3.2 Criar Cluster**
1. Escolha região mais próxima
2. Nome do cluster: "whatsapp-bot"
3. Aguarde criação (2-3 minutos)

### **3.3 Configurar Acesso**
1. **Database Access:**
   - Crie usuário: `botuser`
   - Senha: `senha123` (ou gere automática)
   - Permissões: "Read and write to any database"

2. **Network Access:**
   - Adicione IP: `0.0.0.0/0` (acesso de qualquer lugar)
   - Ou IPs específicos do Render

### **3.4 Obter String de Conexão**
1. Clique "Connect" no cluster
2. Escolha "Connect your application"
3. Copie a string (ex: mongodb+srv://...)
4. Substitua `<password>` pela senha real

---

## ☁️ Passo 4: Configurar Cloudinary (Opcional)

### **4.1 Criar Conta**
1. Acesse https://cloudinary.com/
2. Crie conta gratuita
3. Confirme email

### **4.2 Obter Credenciais**
1. No dashboard, vá em "Settings"
2. Copie:
   - **Cloud Name**
   - **API Key**
   - **API Secret**

---

## 📂 Passo 5: Preparar Código

### **5.1 Fork do Repositório**
1. Acesse o repositório no GitHub
2. Clique "Fork" no canto superior direito
3. Escolha sua conta pessoal

### **5.2 Clonar Localmente (Opcional)**
```bash
git clone https://github.com/SEU-USUARIO/bot-cotacao-ultramsg.git
cd bot-cotacao-ultramsg
```

### **5.3 Configurar Variáveis**
1. Copie `.env.example` para `.env`
2. Preencha todas as variáveis:

```env
# UltraMsg
ULTRAMSG_INSTANCE_ID=instance135696
ULTRAMSG_TOKEN=qtnijalhyl2zhydy

# OpenAI
OPENAI_API_KEY=sk-sua-chave-aqui

# Flask
FLASK_SECRET_KEY=uma-chave-super-secreta-aqui
BASE_URL=https://seu-app.onrender.com

# MongoDB
MONGO_URI=mongodb+srv://botuser:senha123@cluster.mongodb.net/whatsapp_bot

# Cloudinary (opcional)
CLOUDINARY_CLOUD_NAME=seu_cloud_name
CLOUDINARY_API_KEY=sua_api_key
CLOUDINARY_API_SECRET=sua_api_secret

# Agentes
AGENTS=admin
AGENT_admin_EMAIL=admin@equinos.com
AGENT_admin_PASSWORD=admin123
```

---

## 🚀 Passo 6: Deploy no Render

### **6.1 Criar Conta Render**
1. Acesse https://render.com/
2. Faça login com GitHub
3. Autorize acesso aos repositórios

### **6.2 Criar Web Service**
1. Clique "New +" → "Web Service"
2. Conecte seu repositório fork
3. Configure:
   - **Name:** `bot-cotacao-seguros`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
   - **Plan:** Free

### **6.3 Configurar Environment Variables**
Adicione todas as variáveis do arquivo `.env`:

| Key | Value |
|-----|-------|
| `ULTRAMSG_INSTANCE_ID` | instance135696 |
| `ULTRAMSG_TOKEN` | qtnijalhyl2zhydy |
| `OPENAI_API_KEY` | sk-sua-chave-aqui |
| `FLASK_SECRET_KEY` | uma-chave-super-secreta |
| `BASE_URL` | https://bot-cotacao-seguros.onrender.com |
| `MONGO_URI` | mongodb+srv://... |
| `CLOUDINARY_CLOUD_NAME` | seu_cloud_name |
| `CLOUDINARY_API_KEY` | sua_api_key |
| `CLOUDINARY_API_SECRET` | sua_api_secret |
| `AGENTS` | admin |
| `AGENT_admin_EMAIL` | admin@equinos.com |
| `AGENT_admin_PASSWORD` | admin123 |

### **6.4 Deploy**
1. Clique "Create Web Service"
2. Aguarde build (5-10 minutos)
3. Verifique se status é "Live"
4. Anote a URL: `https://bot-cotacao-seguros.onrender.com`

---

## 🔗 Passo 7: Configurar Webhook

### **7.1 No UltraMsg**
1. Volte ao dashboard UltraMsg
2. Vá em "Webhook Settings"
3. Configure:
   - **Webhook URL:** `https://bot-cotacao-seguros.onrender.com/webhook/ultramsg`
   - **Events:** Marque apenas "Message"
4. Clique "Save"

### **7.2 Testar Webhook**
1. Acesse: `https://bot-cotacao-seguros.onrender.com/health`
2. Deve retornar JSON com status "healthy"
3. Teste: `https://bot-cotacao-seguros.onrender.com/webhook/test`

---

## ✅ Passo 8: Testes

### **8.1 Teste Básico**
1. Envie mensagem para seu WhatsApp Business:
   ```
   Olá, quero fazer uma cotação
   ```
2. Bot deve responder em até 10 segundos

### **8.2 Teste Completo**
1. **Mensagem inicial:**
   ```
   Olá, quero cotação para meu cavalo
   ```

2. **Fornecer dados:**
   ```
   Nome é Thunder, vale R$ 50.000, é Quarto de Milha, 
   nasceu em 15/03/2018, é macho castrado, uso para lazer, 
   cocheira em Campinas CEP 13100-000
   ```

3. **Verificar:**
   - Bot coleta dados automaticamente
   - Confirma informações
   - Inicia processo de cotação

### **8.3 Teste do Painel**
1. Acesse: `https://bot-cotacao-seguros.onrender.com/agent/login`
2. Login: `admin@equinos.com` / `admin123`
3. Verifique dashboard com estatísticas

---

## 🔧 Passo 9: Configurações Avançadas

### **9.1 Automação SwissRe (Opcional)**
Se você tem acesso ao sistema SwissRe:

```env
SWISSRE_LOGIN_URL=https://sistema.swissre.com/login
SWISSRE_USERNAME=seu_usuario
SWISSRE_PASSWORD=sua_senha
SWISSRE_HEADLESS=True
```

### **9.2 Múltiplos Agentes**
```env
AGENTS=agent1,agent2,supervisor
AGENT_agent1_EMAIL=joao@equinos.com
AGENT_agent1_PASSWORD=senha123
AGENT_agent2_EMAIL=maria@equinos.com
AGENT_agent2_PASSWORD=senha456
AGENT_supervisor_EMAIL=supervisor@equinos.com
AGENT_supervisor_PASSWORD=senha789
```

### **9.3 Configurações de Áudio**
```env
TTS_ENABLED=True
TTS_LANGUAGE=pt-BR
```

---

## 📊 Passo 10: Monitoramento

### **10.1 Logs do Render**
1. No dashboard Render, clique no seu service
2. Vá na aba "Logs"
3. Monitore mensagens em tempo real

### **10.2 Métricas Importantes**
- ✅ Mensagens processadas com sucesso
- ❌ Erros de webhook
- 🔄 Tempo de resposta
- 📊 Conversas ativas

### **10.3 Alertas**
Configure alertas para:
- Erros frequentes
- Alto uso de OpenAI
- Falhas de conexão MongoDB
- Webhook offline

---

## 🚨 Troubleshooting

### **Problema: Bot não responde**

**Diagnóstico:**
```bash
# Teste health check
curl https://bot-cotacao-seguros.onrender.com/health

# Teste webhook
curl -X POST https://bot-cotacao-seguros.onrender.com/webhook/test
```

**Soluções:**
1. Verifique logs no Render
2. Confirme webhook URL no UltraMsg
3. Teste OPENAI_API_KEY
4. Verifique MONGO_URI

### **Problema: Erro 500 no deploy**

**Soluções:**
1. Verifique todas as environment variables
2. Confirme runtime.txt (Python 3.11)
3. Teste requirements.txt localmente
4. Verifique logs de build

### **Problema: Webhook timeout**

**Soluções:**
1. Otimize processamento de mensagens
2. Use processamento assíncrono
3. Upgrade plano Render
4. Implemente cache

### **Problema: PDF não é enviado**

**Soluções:**
1. Configure Cloudinary corretamente
2. Verifique automação SwissRe
3. Teste upload manual
4. Confirme permissões de arquivo

---

## 🎯 Próximos Passos

### **Curto Prazo (1 semana)**
- [ ] Testar todas as funcionalidades
- [ ] Configurar alertas de monitoramento
- [ ] Treinar equipe no painel de agente
- [ ] Documentar processos internos

### **Médio Prazo (1 mês)**
- [ ] Implementar métricas avançadas
- [ ] Otimizar respostas do bot
- [ ] Adicionar novos campos se necessário
- [ ] Configurar backup automático

### **Longo Prazo (3 meses)**
- [ ] Integrar com CRM/ERP
- [ ] Implementar IA avançada
- [ ] Expandir para outros produtos
- [ ] Escalar para alto volume

---

## 📞 Suporte

### **Problemas Técnicos**
1. Verifique logs primeiro
2. Consulte documentação oficial
3. Teste em ambiente local
4. Entre em contato se necessário

### **Contatos**
- 📧 Email: suporte@equinos.com
- 💬 WhatsApp: +55 19 9 8811-8043
- 🌐 Site: https://equinos.com

---

**✅ Implementação concluída com sucesso!**

Seu bot está agora operacional e pronto para automatizar cotações de seguros equinos via WhatsApp.

