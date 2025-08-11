# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - UltraMsg (Versão Completa Melhorada)
"""

import os
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

# Importar módulos personalizados
try:
    from database_manager import db_manager
    from response_generator import response_generator
except ImportError:
    # Fallback se os módulos não estiverem disponíveis
    db_manager = None
    response_generator = None

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configurações UltraMsg
ULTRAMSG_INSTANCE_ID = os.getenv('ULTRAMSG_INSTANCE_ID')
ULTRAMSG_TOKEN = os.getenv('ULTRAMSG_TOKEN')
ULTRAMSG_BASE_URL = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}"

# Fallback para armazenamento simples se database_manager não estiver disponível
if not db_manager:
    simple_storage = {}

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
        
        logger.info(f"📤 Enviando mensagem para {clean_phone}: {message[:50]}...")
        
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

def process_message_simple(phone, message):
    """Processamento simples de mensagem (fallback)"""
    global simple_storage
    
    if phone not in simple_storage:
        simple_storage[phone] = {'count': 0, 'data': {}}
    
    simple_storage[phone]['count'] += 1
    count = simple_storage[phone]['count']
    
    if count == 1:
        return """🐴 *Olá! Bem-vindo à Equinos Seguros!*

Sou seu assistente virtual e vou te ajudar a fazer a cotação do seguro do seu equino.

Para gerar sua cotação, preciso de algumas informações sobre seu animal:

📋 *DADOS NECESSÁRIOS:*
• Nome do Animal
• Valor do Animal (R$)
• Número de Registro ou Passaporte
• Raça
• Data de Nascimento
• Sexo (inteiro, castrado ou fêmea)
• Utilização (lazer, salto, laço, etc.)
• Endereço da Cocheira (CEP e cidade)

Pode enviar as informações aos poucos. Vou te ajudar! 😊"""
    
    else:
        return f"""📝 *Obrigado pela mensagem #{count}!*

Recebi: "{message}"

Continue enviando as informações do seu animal. Quando tiver todos os dados, vou processar sua cotação!

*Ainda preciso de:*
• Nome, valor, raça, sexo, data de nascimento
• Registro, utilização, endereço da cocheira

Estou aqui para ajudar! 🤝"""

@app.route('/')
def home():
    """Página inicial"""
    return jsonify({
        "status": "online",
        "service": "Bot de Cotação de Seguros - UltraMsg Melhorado",
        "version": "2.2.0",
        "features": [
            "Coleta inteligente de dados com IA",
            "Persistência de informações",
            "Respostas contextuais personalizadas",
            "Validação automática de campos",
            "Formatação profissional",
            "Dashboard de monitoramento"
        ],
        "endpoints": {
            "webhook": "/webhook/ultramsg",
            "health": "/health",
            "test": "/webhook/test",
            "agent": "/agent/login",
            "data": "/api/client-data",
            "stats": "/api/statistics"
        }
    })

@app.route('/health')
def health_check():
    """Health check"""
    stats = {}
    if db_manager:
        stats = db_manager.get_statistics()
    else:
        stats = {
            "total_clients": len(simple_storage),
            "total_conversations": sum(data.get('count', 0) for data in simple_storage.values())
        }
    
    return jsonify({
        "status": "healthy",
        "timestamp": str(datetime.utcnow()),
        "components": {
            "flask": "ok",
            "ultramsg": "ok" if ULTRAMSG_TOKEN else "not_configured",
            "database_manager": "ok" if db_manager else "fallback",
            "response_generator": "ok" if response_generator else "fallback"
        },
        "stats": stats
    }), 200

@app.route('/webhook/ultramsg', methods=['POST'])
def webhook_ultramsg():
    """Webhook para UltraMsg - Versão Melhorada"""
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
        
        # Validar dados essenciais
        if not phone_number or not message_body:
            logger.warning(f"Dados incompletos - Phone: {phone_number}, Body: {message_body}")
            return jsonify({"status": "incomplete_data"}), 400
        
        # Ignorar mensagens próprias
        if message_data.get('fromMe', False):
            logger.info("Mensagem própria ignorada")
            return jsonify({"status": "own_message_ignored"}), 200
        
        logger.info(f"📱 Mensagem de {sender_name} ({phone_number}): {message_body}")
        
        # Processar mensagem com sistema inteligente ou fallback
        if db_manager and response_generator:
            # Sistema completo
            client_data = db_manager.get_client_data(phone_number) or {'data': {}, 'conversation_count': 0}
            
            # Gerar resposta inteligente
            bot_response = response_generator.generate_response(
                phone_number, 
                message_body, 
                client_data, 
                client_data.get('conversation_count', 0)
            )
            
            # Extrair e salvar dados
            existing_data = client_data.get('data', {})
            updated_data = response_generator.extract_animal_data(message_body, existing_data)
            
            # Salvar no banco
            db_manager.save_client_data(phone_number, updated_data)
            db_manager.save_conversation(phone_number, message_body, bot_response)
            
            logger.info(f"🧠 Processamento inteligente concluído")
            
        else:
            # Sistema simples (fallback)
            bot_response = process_message_simple(phone_number, message_body)
            logger.info(f"📝 Processamento simples concluído")
        
        # Enviar resposta
        result = send_ultramsg_message(phone_number, bot_response)
        
        if result.get('success'):
            logger.info(f"✅ Resposta enviada com sucesso")
            return jsonify({
                "status": "success",
                "message_received": message_body,
                "response_sent": bot_response,
                "sender": sender_name,
                "processing_mode": "intelligent" if (db_manager and response_generator) else "simple",
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

@app.route('/api/client-data', methods=['GET'])
def get_client_data():
    """API para visualizar dados dos clientes"""
    if db_manager:
        return jsonify(db_manager.get_all_clients())
    else:
        return jsonify(simple_storage)

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """API para estatísticas"""
    if db_manager:
        return jsonify(db_manager.get_statistics())
    else:
        return jsonify({
            "total_clients": len(simple_storage),
            "total_conversations": sum(data.get('count', 0) for data in simple_storage.values()),
            "mode": "simple"
        })

@app.route('/webhook/test', methods=['GET', 'POST'])
def webhook_test():
    """Teste do webhook"""
    try:
        test_phone = "5519988118043@c.us"
        test_message = "Olá, quero fazer uma cotação para meu cavalo Relâmpago, ele vale R$ 50.000"
        
        # Simular processamento
        if db_manager and response_generator:
            client_data = db_manager.get_client_data(test_phone) or {'data': {}, 'conversation_count': 0}
            bot_response = response_generator.generate_response(
                test_phone, test_message, client_data, client_data.get('conversation_count', 0)
            )
            mode = "intelligent"
        else:
            bot_response = process_message_simple(test_phone, test_message)
            mode = "simple"
        
        return jsonify({
            "status": "test_success",
            "test_message": test_message,
            "bot_response": bot_response,
            "processing_mode": mode,
            "ultramsg_configured": bool(ULTRAMSG_TOKEN),
            "components": {
                "database_manager": bool(db_manager),
                "response_generator": bool(response_generator)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Template para painel de agente
AGENT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Painel de Agente - Equinos Seguros</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 30px; }
        .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0056b3; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; border: 1px solid #dee2e6; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
        .feature-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }
        .feature-card { background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; }
        .code { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Painel de Agente - Bot Melhorado v2.2</h1>
        
        <div class="status success">
            ✅ <strong>Bot Inteligente Online</strong> - Sistema completo funcionando
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.get('total_clients', 0) }}</div>
                <div>Clientes Ativos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.get('completed_clients', 0) }}</div>
                <div>Cotações Completas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.get('total_conversations', 0) }}</div>
                <div>Conversas Totais</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ "%.1f"|format(stats.get('completion_rate', 0)) }}%</div>
                <div>Taxa de Conclusão</div>
            </div>
        </div>
        
        <div class="feature-list">
            <div class="feature-card">
                <h4>🧠 Inteligência Artificial</h4>
                <p>Extração automática de dados usando OpenAI GPT-3.5</p>
            </div>
            <div class="feature-card">
                <h4>💾 Persistência de Dados</h4>
                <p>Armazenamento inteligente de informações dos clientes</p>
            </div>
            <div class="feature-card">
                <h4>💬 Respostas Contextuais</h4>
                <p>Mensagens personalizadas baseadas no histórico</p>
            </div>
            <div class="feature-card">
                <h4>✅ Validação Automática</h4>
                <p>Verificação de campos obrigatórios em tempo real</p>
            </div>
        </div>
        
        <div class="status info">
            📊 <strong>Componentes do Sistema:</strong><br>
            • Database Manager: {{ 'Ativo' if db_manager else 'Fallback Simples' }}<br>
            • Response Generator: {{ 'Ativo' if response_generator else 'Fallback Simples' }}<br>
            • UltraMsg API: {{ 'Configurado' if ultramsg_configured else 'Não configurado' }}<br>
            • OpenAI: {{ 'Configurado' if openai_configured else 'Não configurado' }}
        </div>
        
        <div class="status success">
            🎯 <strong>Campos Coletados Automaticamente:</strong><br>
            • Nome do Animal • Valor do Animal (R$) • Número de Registro/Passaporte<br>
            • Raça • Data de Nascimento • Sexo (inteiro/castrado/fêmea)<br>
            • Utilização (lazer/salto/laço) • Endereço da Cocheira
        </div>
        
        <h3>🔧 Ações Disponíveis:</h3>
        <a href="javascript:location.reload()" class="btn">🔄 Atualizar Status</a>
        <a href="/api/client-data" target="_blank" class="btn">📊 Ver Dados dos Clientes</a>
        <a href="/api/statistics" target="_blank" class="btn">📈 Estatísticas</a>
        <a href="/webhook/test" target="_blank" class="btn">🧪 Testar Bot</a>
        
        <h3>📱 Como Testar:</h3>
        <div class="code">
            1. Envie uma mensagem para seu WhatsApp Business<br>
            2. Teste: "Olá, quero cotação para meu cavalo Thor, vale R$ 80.000"<br>
            3. Veja a resposta inteligente e formatada<br>
            4. Continue enviando dados e veja como o bot organiza tudo
        </div>
        
        <div class="status warning">
            🚀 <strong>Próximas Melhorias:</strong><br>
            • Integração com MongoDB para persistência permanente<br>
            • Geração automática de cotações com SwissRe<br>
            • Envio de PDFs via WhatsApp<br>
            • Dashboard com métricas em tempo real<br>
            • Sistema de notificações para agentes
        </div>
    </div>
</body>
</html>
"""

@app.route('/agent/login')
def agent_login():
    """Painel de agente"""
    if db_manager:
        stats = db_manager.get_statistics()
    else:
        stats = {
            "total_clients": len(simple_storage),
            "total_conversations": sum(data.get('count', 0) for data in simple_storage.values()),
            "completed_clients": 0,
            "completion_rate": 0
        }
    
    return render_template_string(AGENT_TEMPLATE, 
                                stats=stats,
                                db_manager=bool(db_manager),
                                response_generator=bool(response_generator),
                                ultramsg_configured=bool(ULTRAMSG_TOKEN),
                                openai_configured=bool(os.getenv("OPENAI_API_KEY")))

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint não encontrado",
        "available_endpoints": [
            "/", "/health", "/webhook/ultramsg", "/webhook/test", 
            "/agent/login", "/api/client-data", "/api/statistics"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {str(error)}")
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Iniciando Bot Melhorado v2.2 na porta {port}")
    logger.info(f"📡 UltraMsg API URL: {ULTRAMSG_BASE_URL}")
    logger.info(f"🧠 Database Manager: {'Ativo' if db_manager else 'Fallback'}")
    logger.info(f"💬 Response Generator: {'Ativo' if response_generator else 'Fallback'}")
    app.run(host='0.0.0.0', port=port, debug=False)