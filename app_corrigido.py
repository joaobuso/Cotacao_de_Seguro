# -*- coding: utf-8 -*-
"""
Aplicação Principal - Bot de Cotação de Seguros UltraMsg
"""

import os
import logging
from flask import Flask, request, jsonify, session
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

logger = logging.getLogger(__name__)

def create_app():
    """
    Factory function para criar a aplicação Flask
    """
    app = Flask(__name__)
    
    # Configurações
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Importar módulos após criar app para evitar circular imports
    try:
        from app.integrations.ultramsg_api import ultramsg_api
        from app.bot.message_handler import MessageHandler
        from app.agent.routes import agent_bp
        
        logger.info("✅ Módulos importados com sucesso")
        
    except ImportError as e:
        logger.warning(f"⚠️ Erro ao importar módulos: {e}")
        # Continuar sem os módulos para permitir que a app inicie
        ultramsg_api = None
        MessageHandler = None
        agent_bp = None
    
    # Inicializar handler de mensagens
    if MessageHandler:
        message_handler = MessageHandler()
    else:
        message_handler = None
    
    # Registrar blueprints
    if agent_bp:
        app.register_blueprint(agent_bp)
        logger.info("✅ Blueprint de agente registrado")
    
    @app.route('/')
    def home():
        """Página inicial"""
        return jsonify({
            "status": "online",
            "service": "Bot de Cotação de Seguros - UltraMsg",
            "version": "2.0.0",
            "endpoints": {
                "webhook": "/webhook/ultramsg",
                "health": "/health",
                "test": "/webhook/test",
                "agent": "/agent/login"
            }
        })
    
    @app.route('/health')
    def health_check():
        """Health check para monitoramento"""
        try:
            # Verificar componentes essenciais
            health_status = {
                "status": "healthy",
                "timestamp": str(datetime.utcnow()),
                "components": {
                    "flask": "ok",
                    "ultramsg_api": "ok" if ultramsg_api else "not_configured",
                    "message_handler": "ok" if message_handler else "not_configured",
                    "openai": "ok" if os.getenv('OPENAI_API_KEY') else "not_configured",
                    "mongodb": "unknown"  # Seria necessário testar conexão
                }
            }
            
            return jsonify(health_status), 200
            
        except Exception as e:
            logger.error(f"Erro no health check: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500
    
    @app.route('/webhook/ultramsg', methods=['POST'])
    def webhook_ultramsg():
        """Webhook para receber mensagens do UltraMsg"""
        try:
            if not message_handler:
                return jsonify({"error": "Message handler não configurado"}), 500
            
            # Obter dados da requisição
            data = request.get_json()
            
            if not data:
                logger.warning("Webhook recebido sem dados")
                return jsonify({"status": "no_data"}), 400
            
            # Log da mensagem recebida
            logger.info(f"Webhook recebido: {data}")
            
            # Extrair informações da mensagem
            phone_number = data.get('from', '')
            message_body = data.get('body', '')
            message_type = data.get('type', 'text')
            
            if not phone_number:
                logger.warning("Webhook sem número de telefone")
                return jsonify({"status": "no_phone"}), 400
            
            # Processar mensagem
            result = message_handler.process_message(
                phone_number=phone_number,
                message_body=message_body,
                message_type=message_type,
                message_data=data
            )
            
            logger.info(f"Mensagem processada: {result.get('status')}")
            
            return jsonify({
                "status": "success",
                "result": result
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no webhook: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
    
    @app.route('/webhook/test', methods=['GET', 'POST'])
    def webhook_test():
        """Endpoint para testar webhook"""
        try:
            test_data = {
                "from": "+5519988118043",
                "body": "Teste do webhook",
                "type": "text",
                "timestamp": "1234567890"
            }
            
            if message_handler:
                result = message_handler.process_message(
                    phone_number=test_data['from'],
                    message_body=test_data['body'],
                    message_type=test_data['type'],
                    message_data=test_data
                )
                
                return jsonify({
                    "status": "test_success",
                    "message": "Webhook testado com sucesso",
                    "result": result
                }), 200
            else:
                return jsonify({
                    "status": "test_partial",
                    "message": "Webhook funcionando, mas handler não configurado"
                }), 200
                
        except Exception as e:
            logger.error(f"Erro no teste de webhook: {str(e)}")
            return jsonify({
                "status": "test_error",
                "error": str(e)
            }), 500
    
    @app.route('/api/send-message', methods=['POST'])
    def send_message():
        """API para enviar mensagens manualmente"""
        try:
            if not ultramsg_api:
                return jsonify({"error": "UltraMsg API não configurada"}), 500
            
            data = request.get_json()
            phone = data.get('phone')
            message = data.get('message')
            
            if not phone or not message:
                return jsonify({"error": "Phone e message são obrigatórios"}), 400
            
            # Enviar mensagem
            result = ultramsg_api.send_text_message(phone, message)
            
            return jsonify(result), 200 if result.get('success') else 500
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handler para 404"""
        return jsonify({
            "error": "Endpoint não encontrado",
            "available_endpoints": [
                "/",
                "/health",
                "/webhook/ultramsg",
                "/webhook/test",
                "/api/send-message",
                "/agent/login"
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler para 500"""
        logger.error(f"Erro interno: {str(error)}")
        return jsonify({
            "error": "Erro interno do servidor",
            "message": "Verifique os logs para mais detalhes"
        }), 500
    
    # Importar datetime aqui para evitar erro
    from datetime import datetime
    
    logger.info("✅ Aplicação Flask configurada com sucesso")
    return app

# Criar instância da aplicação
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando aplicação na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)