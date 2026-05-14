# Build context: project root (same pattern as src/ingress/Dockerfile)
# ---------------------------------------------------------------------------
# Stage 1 — builder: install deps and generate Python proto stubs
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

COPY src/processor/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Generate Python stubs from the shared event.proto (Phase 2 source of truth).
COPY src/ingress/event.proto ./proto/event.proto
RUN python -m grpc_tools.protoc \
        -I ./proto \
        --python_out=./proto \
        --grpc_python_out=./proto \
        ./proto/event.proto \
    && touch ./proto/__init__.py

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages

# Generated proto stubs land in /app/proto/ — importable as `from proto import event_pb2`
COPY --from=builder /build/proto/ ./proto/

# Processor source (flat layout — all modules importable directly)
COPY src/processor/ ./

ENV KAFKA_BROKERS="kafka:29092"
ENV KAFKA_TOPIC="events"
ENV STATE_TOPIC="state-updates"
ENV HEARTBEAT_TOPIC="heartbeats"
ENV NODE_ID="worker-1"
ENV ALL_NODES="worker-1,worker-2"

CMD ["python", "main.py"]
