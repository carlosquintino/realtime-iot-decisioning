# Imagem do serviço `decisioning` (feature da plataforma Magistrala).
# Build context = raiz do repo (ver docker/addons/decisioning/docker-compose.yaml).
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Dependências primeiro (cache de layer).
COPY src/requirements.txt /app/src/requirements.txt
RUN pip install --no-cache-dir -r /app/src/requirements.txt

# Código do serviço.
COPY src/ /app/src/

CMD ["python", "-m", "src.consumer"]
