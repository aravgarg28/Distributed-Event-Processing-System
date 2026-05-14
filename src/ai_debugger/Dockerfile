# Build context: project root
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/ai_debugger/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ai_debugger/ .

# Docker socket is mounted at runtime via docker-compose volume
ENV WATCH_CONTAINERS="ingress,processor-1,processor-2"
ENV POLL_INTERVAL_SECONDS="30"
ENV ERROR_THRESHOLD="5"
ENV WINDOW_SECONDS="60"
ENV GRAFANA_URL="http://grafana:3000"
ENV GRAFANA_API_TOKEN=""
ENV GROQ_API_KEY=""
ENV LLM_MODEL="llama-3.3-70b-versatile"

CMD ["python", "main.py"]
