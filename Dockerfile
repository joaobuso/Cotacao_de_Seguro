# /home/ubuntu/whatsapp_handoff_project/Dockerfile

# Usar uma imagem base oficial do Python
FROM python:3.9-slim

# Definir o diretório de trabalho no contêiner
WORKDIR /app

# Copiar o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt requirements.txt

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da aplicação para o diretório de trabalho
# Incluindo a pasta "app" e outros arquivos como .env (se for incluído na build, não recomendado para produção)
COPY . .

# Expor a porta que o Flask (ou Gunicorn) estará rodando
EXPOSE 5000

# Comando para rodar a aplicação quando o contêiner iniciar
# Usar Gunicorn para produção é recomendado
# O arquivo .env deve ser gerenciado fora do contêiner em produção (ex: via segredos do Docker ou variáveis de ambiente do host)
# Para desenvolvimento, você pode copiar o .env, mas para produção, use variáveis de ambiente.
# Este CMD assume que você terá um arquivo .env no diretório /app ou que as variáveis estão setadas no ambiente do contêiner.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]

# Se não quiser usar Gunicorn e apenas Flask (para desenvolvimento/teste simples):
# CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

