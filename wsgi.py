#!/usr/bin/env python3
"""
WSGI entry point - Porta Corrigida para Render
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FORÇAR PORTA CORRETA
PORT = int(os.environ.get('PORT', 8080))
logger.info(f"🔧 Porta configurada: {PORT}")

try:
    logger.info("🔄 Importando aplicação...")
    
    # Importar aplicação
    from main import app
    
    logger.info("✅ Aplicação importada com sucesso")
    
    # Verificar configurações
    mongo_uri = os.getenv('MONGO_URI')
    ultramsg_instance = os.getenv('ULTRAMSG_INSTANCE_ID')
    ultramsg_token = os.getenv('ULTRAMSG_TOKEN')
    
    logger.info(f"🗄️ MongoDB: {'Configurado' if mongo_uri else 'Não configurado'}")
    logger.info(f"📡 UltraMsg Instance: {ultramsg_instance or 'Não configurado'}")
    logger.info(f"🔑 UltraMsg Token: {'Configurado' if ultramsg_token else 'Não configurado'}")
    
    logger.info(f"🚀 WSGI pronto na porta {PORT}")

except Exception as e:
    logger.error(f"❌ Erro crítico: {str(e)}")
    raise

# Exportar para Gunicorn
application = app

if __name__ == "__main__":
    logger.info(f"🚀 Executando diretamente na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)