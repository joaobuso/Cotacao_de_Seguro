import os

# Configuração do Gunicorn para Render
bind = f"0.0.0.0:{os.environ.get('PORT', 8080)}"
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

print(f"🔧 Gunicorn configurado para porta: {os.environ.get('PORT', 8080)}")

