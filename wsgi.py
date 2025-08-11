# -*- coding: utf-8 -*-
"""
WSGI Entry Point Simplificado - Bot UltraMsg
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Importar a aplicação diretamente
    from main_simples import app
    
    logger.info("✅ Aplicação importada com sucesso")
    
except ImportError as e:
    logger.error(f"❌ Erro de importação: {e}")
    raise

except Exception as e:
    logger.error(f"❌ Erro geral: {e}")
    raise

# Para debug local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)