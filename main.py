# -*- coding: utf-8 -*-
"""
Bot de Cotação de Seguros - UltraMsg (Encoding Corrigido)
"""

import os
import logging
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

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

# Armazenamento simples de dados dos clientes
client_data = {}

# Campos obrigatórios para cotação
REQUIRED_FIELDS = {
    'nome_animal': 'Nome do Animal',
    'valor_animal': 'Valor do Animal (R$)',
    'registro': 'Numero de Registro ou Passaporte',
    'raca': 'Raca',
    'data_nascimento': 'Data de Nascimento',
    'sexo': 'Sexo (inteiro, castrado ou femea)',
    'utilizacao': 'Utilizacao (lazer, salto, laco, etc.)',
    'endereco_cocheira': 'Endereco da Cocheira (CEP e cidade)'
}

def clean_text_for_whatsapp(text):
    """Remove ou substitui caracteres que causam problemas no WhatsApp"""
    # Substituir caracteres especiais por versões simples
    replacements = {
        'ç': 'c', 'Ç': 'C',
        'ã': 'a', 'Ã': 'A',
        'á': 'a', 'Á': 'A',
        'à': 'a', 'À': 'A',
        'â': 'a', 'Â': 'A',
        'é': 'e', 'É': 'E',
        'ê': 'e', 'Ê': 'E',
        'í': 'i', 'Í': 'I',
        'ó': 'o', 'Ó': 'O',
        'ô': 'o', 'Ô': 'O',
        'õ': 'o', 'Õ': 'O',
        'ú': 'u', 'Ú': 'U',
        'ü': 'u', 'Ü': 'U'
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text

def send_ultramsg_message(phone, message):
    """Envia mensagem via UltraMsg com encoding correto"""
    try:
        url = f"{ULTRAMSG_BASE_URL}/messages/chat"
        
        # Limpar número de telefone
        clean_phone = phone.replace('@c.us', '').replace('+', '')
        
        # Limpar texto para evitar problemas de encoding
        clean_message = clean_text_for_whatsapp(message)
        
        # Preparar dados
        data = {
            'token': ULTRAMSG_TOKEN,
            'to': clean_phone,
            'body': clean_message
        }
        
        # Usar URL encoding adequado
        payload = urllib.parse.urlencode(data, encoding='utf-8')
        
        headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        
        logger.info(f"📤 Enviando mensagem para {clean_phone}: {clean_message[:50]}...")
        
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

def extract_animal_data_simple(message, existing_data=None):
    """Extração simples de dados sem caracteres especiais"""
    import re
    
    data = existing_data.copy() if existing_data else {}
    message_lower = message.lower()
    
    # Padrões simples de extração
    patterns = {
        'nome_animal': [
            r'nome[:\s]+([a-z\s]+)', 
            r'chama[:\s]+([a-z\s]+)',
            r'cavalo[:\s]+([a-z\s]+)',
            r'egua[:\s]+([a-z\s]+)'
        ],
        'valor_animal': [
            r'valor[:\s]*r?\$?\s*([0-9.,]+)', 
            r'vale[:\s]*r?\$?\s*([0-9.,]+)',
            r'custa[:\s]*r?\$?\s*([0-9.,]+)'
        ],
        'raca': [
            r'raca[:\s]+([a-z\s]+)', 
            r'e\s+um[a]?\s+([a-z\s]+)',
            r'quarto\s+de\s+milha',
            r'mangalarga',
            r'puro\s+sangue'
        ],
        'sexo': [r'(inteiro|castrado|femea|macho|egua)'],
        'utilizacao': [r'(lazer|salto|laco|corrida|trabalho|esporte)'],
        'registro': [
            r'registro[:\s]*([a-z0-9]+)',
            r'passaporte[:\s]*([a-z0-9]+)'
        ],
        'data_nascimento': [
            r'nasceu[:\s]*([0-9/]+)',
            r'nascimento[:\s]*([0-9/]+)',
            r'([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})'
        ]
    }
    
    for field, pattern_list in patterns.items():
        if field not in data or not data[field]:
            for pattern in pattern_list:
                match = re.search(pattern, message_lower)
                if match:
                    value = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                    data[field] = value
                    break
    
    return data

def generate_response_message(phone, message):
    """Gera resposta personalizada baseada nos dados coletados"""
    try:
        # Inicializar dados do cliente se não existir
        if phone not in client_data:
            client_data[phone] = {'data': {}, 'conversation_count': 0}
        
        client_data[phone]['conversation_count'] += 1
        count = client_data[phone]['conversation_count']
        
        # Extrair dados da mensagem atual
        existing_data = client_data[phone]['data']
        updated_data = extract_animal_data_simple(message, existing_data)
        client_data[phone]['data'] = updated_data
        
        # Verificar campos faltantes
        missing_fields = []
        collected_fields = []
        
        for field_key, field_name in REQUIRED_FIELDS.items():
            if field_key in updated_data and updated_data[field_key]:
                collected_fields.append(f"✅ {field_name}: {updated_data[field_key]}")
            else:
                missing_fields.append(f"❌ {field_name}")
        
        # Gerar resposta baseada no estado
        if count == 1:
            # Primeira mensagem - saudação
            response = """🐴 *Ola! Bem-vindo a Equinos Seguros!*

Sou seu assistente virtual e vou te ajudar a fazer a cotacao do seguro do seu equino de forma rapida e facil.

Para gerar sua cotacao, preciso de algumas informacoes sobre seu animal:

📋 *DADOS NECESSARIOS:*
• Nome do Animal
• Valor do Animal (R$)
• Numero de Registro ou Passaporte
• Raca
• Data de Nascimento
• Sexo (inteiro, castrado ou femea)
• Utilizacao (lazer, salto, laco, etc.)
• Endereco da Cocheira (CEP e cidade)

Voce pode enviar todas as informacoes de uma vez ou ir enviando aos poucos. Vou te ajudar a organizar tudo! 😊

*Como prefere comecar?*"""
        
        elif len(missing_fields) == 0:
            # Todos os dados coletados
            data_summary = "\\n".join(collected_fields)
            
            response = f"""✅ *Perfeito! Coletei todas as informacoes necessarias:*

{data_summary}

🎉 *Sua cotacao esta sendo processada!*

Em breve voce recebera:
• Proposta de seguro personalizada
• Valores e coberturas
• Condicoes especiais

Aguarde alguns instantes... 🔄"""
        
        else:
            # Dados parciais coletados
            collected_list = "\\n".join(collected_fields) if collected_fields else "Nenhum dado coletado ainda."
            missing_list = "\\n".join(missing_fields)
            
            response = f"""📝 *Obrigado pelas informacoes!*

*DADOS JA COLETADOS:*
{collected_list}

*AINDA PRECISO DE:*
{missing_list}

Pode enviar as informacoes que faltam. Estou aqui para te ajudar! 😊"""
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return "Ola! Bem-vindo a Equinos Seguros. Vou ajuda-lo com sua cotacao. Por favor, me informe os dados do seu animal."

@app.route('/')
def home():
    """Página inicial"""
    return jsonify({
        "status": "online",
        "service": "Bot de Cotacao de Seguros - UltraMsg (Encoding Corrigido)",
        "version": "2.3.0",
        "encoding": "UTF-8 com fallback ASCII",
        "endpoints": {
            "webhook": "/webhook/ultramsg",
            "health": "/health",
            "test": "/webhook/test",
            "agent": "/agent/login",
            "data": "/api/client-data"
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
            "encoding": "utf-8_with_ascii_fallback"
        },
        "stats": {
            "active_clients": len(client_data),
            "total_conversations": sum(data.get('conversation_count', 0) for data in client_data.values())
        }
    }), 200

@app.route('/webhook/ultramsg', methods=['POST'])
def webhook_ultramsg():
    """Webhook para UltraMsg - Encoding Corrigido"""
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
        
        # Gerar resposta
        bot_response = generate_response_message(phone_number, message_body)
        
        # Enviar resposta
        result = send_ultramsg_message(phone_number, bot_response)
        
        if result.get('success'):
            logger.info(f"✅ Resposta enviada com sucesso")
            return jsonify({
                "status": "success",
                "message_received": message_body,
                "response_sent": bot_response,
                "sender": sender_name,
                "client_data": client_data.get(phone_number, {}),
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
    return jsonify({
        "total_clients": len(client_data),
        "clients": client_data
    })

@app.route('/webhook/test', methods=['GET', 'POST'])
def webhook_test():
    """Teste do webhook"""
    try:
        test_phone = "5519988118043@c.us"
        test_message = "Ola, quero fazer uma cotacao para meu cavalo Relampago, ele vale R$ 50.000"
        
        # Simular processamento
        bot_response = generate_response_message(test_phone, test_message)
        
        return jsonify({
            "status": "test_success",
            "test_message": test_message,
            "bot_response": bot_response,
            "client_data": client_data.get(test_phone, {}),
            "ultramsg_configured": bool(ULTRAMSG_TOKEN),
            "encoding_test": {
                "original": "Olá, cotação, informações",
                "cleaned": clean_text_for_whatsapp("Olá, cotação, informações")
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
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Painel de Agente - Bot Encoding Corrigido</h1>
        
        <div class="status success">
            ✅ <strong>Bot Online com Encoding Corrigido</strong> - Caracteres especiais funcionando
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ active_clients }}</div>
                <div>Clientes Ativos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_conversations }}</div>
                <div>Conversas Totais</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">8</div>
                <div>Campos Coletados</div>
            </div>
        </div>
        
        <div class="status info">
            🔧 <strong>Correcoes Aplicadas:</strong><br>
            • ✅ Encoding UTF-8 com fallback ASCII<br>
            • ✅ Substituicao de caracteres especiais<br>
            • ✅ Headers corretos para UltraMsg<br>
            • ✅ URL encoding adequado<br>
            • ✅ Texto limpo para WhatsApp
        </div>
        
        <div class="status warning">
            📝 <strong>Caracteres Substituidos:</strong><br>
            ç → c, ã → a, é → e, ô → o, etc.<br>
            Isso garante compatibilidade total com WhatsApp
        </div>
        
        <h3>🔧 Acoes Disponiveis:</h3>
        <button class="btn" onclick="location.reload()">🔄 Atualizar Status</button>
        <button class="btn" onclick="window.open('/api/client-data', '_blank')">📊 Ver Dados dos Clientes</button>
        <button class="btn" onclick="window.open('/webhook/test', '_blank')">🧪 Testar Bot</button>
        
        <div class="status success">
            🎯 <strong>Teste Agora:</strong><br>
            Envie "Ola" para seu WhatsApp Business e veja a mensagem formatada corretamente!
        </div>
    </div>
</body>
</html>
"""

@app.route('/agent/login')
def agent_login():
    """Painel de agente"""
    active_clients = len(client_data)
    total_conversations = sum(data.get('conversation_count', 0) for data in client_data.values())
    
    return render_template_string(AGENT_TEMPLATE, 
                                active_clients=active_clients,
                                total_conversations=total_conversations)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint nao encontrado",
        "available_endpoints": ["/", "/health", "/webhook/ultramsg", "/webhook/test", "/agent/login", "/api/client-data"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {str(error)}")
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Iniciando Bot com Encoding Corrigido na porta {port}")
    logger.info(f"📡 UltraMsg API URL: {ULTRAMSG_BASE_URL}")
    logger.info(f"🔤 Encoding: UTF-8 com fallback ASCII para caracteres especiais")
    app.run(host='0.0.0.0', port=port, debug=False)