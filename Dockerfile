# ─────────────────────────────────────────────
# Dockerfile — GDPRag
# ─────────────────────────────────────────────
# RAG GDPR-compliant con Mistral AI + ChromaDB + Gradio
#
# Build:  docker build -t gdprag .
# Run:    docker compose up
# ─────────────────────────────────────────────

FROM python:3.12-slim

LABEL maintainer="Mediaform s.c.r.l."
LABEL description="GDPRag — RAG GDPR-compliant con Mistral AI"

# Dipendenze di sistema per i parser documenti
RUN apt-get update && apt-get install -y --no-install-recommends \
    antiword \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice
COPY rag_engine.py .
COPY web_ui.py .
COPY config_manager.py .

# Crea cartelle
RUN mkdir -p /data /app/chroma_db /app/config

# Variabili d'ambiente
ENV MISTRAL_API_KEY=""
ENV CHROMA_PATH="/app/chroma_db"
ENV CHAT_MODEL="mistral-small-latest"
ENV HOST="0.0.0.0"
ENV PORT="7860"

# Porta Gradio
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

# Avvia la web UI
CMD ["python", "web_ui.py"]
