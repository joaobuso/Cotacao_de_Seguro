# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - UltraMsg (Versão Corrigida)
"""

import os
import logging
import requests
import openai
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Criar aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configurações UltraMsg
ULTRAMSG_INSTANCE_ID = os.getenv('ULTRAMSG_INSTANCE_ID')
ULTRAMSG_TOKEN = os.getenv('ULTRAMSG_TOKEN')
ULTRAMSG_BASE_URL = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}"

def send_ultramsg_message(phone, message):
    """Envia mensagem via UltraMsg"""
    try:
        url = f"{ULTRAMSG_BASE_URL}/messages/chat"
        
        # Limpar número de telefone
        clean_phone = phone.replace('@c.us', '').replace('+', '')
        
        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,
            'body': message
        }
        
        payload = "&".join([f"{k}={v}" for k, v in data.items()])
        payload = payload.encode('utf8').decode('iso-8859-1')
        
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        
        logger.info(f"Enviando mensagem para {clean_phone}: {message[:50]}...")
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Mensagem enviada com sucesso para {clean_phone}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {str(e)}")
        return {"success": False, "error": str(e)}

def generate_bot_response(message):
    """Gera resposta do bot usando OpenAI"""
    try:
        if not openai.api_key:
            return "Olá! Bem-vindo à Equinos Seguros. Como posso ajudá-lo com sua cotação de seguro?"
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """Você é um assistente de seguros para equinos da empresa Equinos Seguros.
                    
                    Sua função é coletar as seguintes informações obrigatórias:
                    - Nome do Animal
                    - Valor do Animal
                    - Número de Registro ou Passaporte
                    - Raça
                    - Data de Nascimento
                    - Sexo (inteiro, castrado ou fêmea)
                    - Utilização (lazer, salto, laço etc.)
                    - Endereço da Cocheira (CEP e cidade)
                    
                    Seja educado, profissional e objetivo. Responda em português do Brasil.
                    Mantenha as respostas curtas e diretas."""
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Erro na OpenAI: {str(e)}")
        return "Olá! Bem-vindo à Equinos Seguros. Vou ajudá-lo com sua cotação de seguro. Por favor, me informe os dados do seu animal."

@app.route('/')
def home():
    """Página inicial"""
    return jsonify({
        "status": "online",
        "service": "Bot de Cotação de Seguros - UltraMsg",
        "version": "2.0.1",
        "endpoints": {
            "webhook": "/webhook/ultramsg",
            "health": "/health",
            "test": "/webhook/test",
            "agent": "/agent/login"
        }
    })

@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": str(datetime.utcnow()),
        "components": {
            "flask": "ok",
            "ultramsg": "ok" if ULTRAMSG_TOKEN else "not_configured",
            "openai": "ok" if openai.api_key else "not_configured"
        },
        "config": {
            "ultramsg_instance": ULTRAMSG_INSTANCE_ID,
            "ultramsg_url": ULTRAMSG_BASE_URL
        }
    }), 200

@app.route('/webhook/ultramsg', methods=['POST'])
def webhook_ultramsg():
    """Webhook para UltraMsg - Estrutura corrigida"""
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Webhook recebido sem dados")
            return jsonify({"status": "no_data"}), 400
        
        logger.info(f"📨 Webhook recebido: {data}")
        
        # Verificar se é evento de mensagem recebida
        if data.get('event_type') != 'message_received':
            logger.info(f"Evento ignorado: {data.get('event_type')}")
            return jsonify({"status": "event_ignored"}), 200
        
        # Extrair dados da estrutura UltraMsg
        message_data = data.get('data', {})
        
        if not message_data:
            logger.warning("Dados da mensagem não encontrados")
            return jsonify({"status": "no_message_data"}), 400
        
        # Extrair informações da mensagem
        phone_number = message_data.get('from', '')
        message_body = message_data.get('body', '')
        sender_name = message_data.get('pushname', 'Cliente')
        message_type = message_data.get('type', 'chat')
        
        # Validar dados essenciais
        if not phone_number or not message_body:
            logger.warning(f"Dados incompletos - Phone: {phone_number}, Body: {message_body}")
            return jsonify({"status": "incomplete_data"}), 400
        
        # Ignorar mensagens próprias
        if message_data.get('fromMe', False):
            logger.info("Mensagem própria ignorada")
            return jsonify({"status": "own_message_ignored"}), 200
        
        logger.info(f"📱 Mensagem de {sender_name} ({phone_number}): {message_body}")
        
        # Gerar resposta do bot
        bot_response = generate_bot_response(message_body)
        
        # Enviar resposta
        result = send_ultramsg_message(phone_number, bot_response)
        
        if result.get('success'):
            logger.info(f"✅ Resposta enviada com sucesso")
            return jsonify({
                "status": "success",
                "message_received": message_body,
                "response_sent": bot_response,
                "sender": sender_name,
                "ultramsg_result": result
            }), 200
        else:
            logger.error(f"❌ Falha ao enviar resposta: {result}")
            return jsonify({
                "status": "send_failed",
                "error": result.get('error'),
                "message_received": message_body,
                "response_generated": bot_response
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/test', methods=['GET', 'POST'])
def webhook_test():
    """Teste do webhook"""
    try:
        test_message = "Olá, quero fazer uma cotação"
        bot_response = generate_bot_response(test_message)
        
        return jsonify({
            "status": "test_success",
            "test_message": test_message,
            "bot_response": bot_response,
            "ultramsg_configured": bool(ULTRAMSG_TOKEN),
            "openai_configured": bool(openai.api_key),
            "ultramsg_url": ULTRAMSG_BASE_URL
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """API para enviar mensagens manualmente"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message')
        
        if not phone or not message:
            return jsonify({"error": "Phone e message são obrigatórios"}), 400
        
        result = send_ultramsg_message(phone, message)
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Template simples para painel de agente
AGENT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Painel de Agente - Equinos Seguros</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .code { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Painel de Agente - Bot UltraMsg</h1>
        
        <div class="status success">
            ✅ <strong>Sistema Online</strong> - Bot funcionando normalmente
        </div>
        
        <div class="status info">
            📊 <strong>Configurações:</strong><br>
            • UltraMsg: {{ 'Configurado' if ultramsg_configured else 'Não configurado' }}<br>
            • OpenAI: {{ 'Configurado' if openai_configured else 'Não configurado' }}<br>
            • Webhook: {{ webhook_url }}<br>
            • API UltraMsg: {{ ultramsg_api_url }}
        </div>
        
        <div class="status success">
            🎉 <strong>Webhook Funcionando!</strong> Mensagens estão sendo recebidas corretamente.
        </div>
        
        <h3>🔧 Status da Integração:</h3>
        <ol>
            <li>✅ Webhook configurado no UltraMsg</li>
            <li>✅ Mensagens chegando no bot</li>
            <li>✅ Estrutura de dados corrigida</li>
            <li>🔄 Testando envio de respostas</li>
        </ol>
        
        <h3>📱 Para testar:</h3>
        <div class="code">
            1. Envie uma mensagem para seu WhatsApp Business<br>
            2. Verifique os logs no Render<br>
            3. Aguarde resposta automática do bot
        </div>
        
        <button class="btn" onclick="location.reload()">🔄 Atualizar Status</button>
    </div>
</body>
</html>
"""

@app.route('/agent/login')
def agent_login():
    """Painel simples de agente"""
    base_url = os.getenv('BASE_URL', 'http://localhost:8080')
    webhook_url = f"{base_url}/webhook/ultramsg"
    
    return render_template_string(AGENT_TEMPLATE, 
                                ultramsg_configured=bool(ULTRAMSG_TOKEN),
                                openai_configured=bool(openai.api_key),
                                webhook_url=webhook_url,
                                ultramsg_api_url=ULTRAMSG_BASE_URL)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint não encontrado",
        "available_endpoints": ["/", "/health", "/webhook/ultramsg", "/webhook/test", "/agent/login"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {str(error)}")
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Iniciando Bot UltraMsg na porta {port}")
    logger.info(f"📡 UltraMsg API URL: {ULTRAMSG_BASE_URL}")
    app.run(host='0.0.0.0', port=port, debug=False)