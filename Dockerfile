FROM python:3.11-slim

WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código
COPY . .

# Expor porta
EXPOSE 10000

# Iniciar com gunicorn
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000", "--workers", "2", "--threads", "4", "--timeout", "120"]
