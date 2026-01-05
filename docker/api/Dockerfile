# ProtecAI API - Dockerfile
# ========================

FROM python:3.11-slim

LABEL maintainer="ProtecAI Team <protecai@petrobras.com.br>"
LABEL description="Sistema Integrado de Proteção de Relés - API REST"
LABEL version="1.0.0"

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (para cache do Docker)
COPY api/requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY api/ ./api/
COPY src/ ./src/
COPY docs/ ./docs/

# Definir variáveis de ambiente
ENV PYTHONPATH=/app
ENV POSTGRES_SERVER=postgres-protecai
ENV POSTGRES_USER=protecai
ENV POSTGRES_PASSWORD=protecai
ENV POSTGRES_DB=protecai_db
ENV POSTGRES_PORT=5432

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]