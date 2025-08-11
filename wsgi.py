# -*- coding: utf-8 -*-
"""
WSGI entry point para o Bot de Cotação de Seguros - UltraMsg
Arquivo para deployment no Render, Railway, Heroku, etc.
"""

import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar a aplicação
from app import app

# Criar diretórios necessários
os.makedirs('static_bot_audio', exist_ok=True)
os.makedirs('static_files', exist_ok=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

