# Build context: project root (docker compose uses context: .)
# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler \
    protobuf-compiler-grpc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only what the ingress CMakeLists needs — keeps layer cache granular.
COPY src/ingress/ src/ingress/

RUN cmake \
        -S src/ingress \
        -B cmake-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF \
    && cmake --build cmake-build --target ingress_server -j"$(nproc)"

# ---------------------------------------------------------------------------
# Stage 2 — runtime (minimal image)
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgrpc++1 \
    libprotobuf23 \
    librdkafka1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/cmake-build/ingress_server ./ingress_server

# gRPC listener for event producers
EXPOSE 50051
# Prometheus metrics scrape endpoint (wired in Phase 4)
EXPOSE 8080

ENV KAFKA_BROKERS="kafka:29092"
ENV KAFKA_TOPIC="events"
ENV GRPC_LISTEN_ADDRESS="0.0.0.0:50051"

CMD ["./ingress_server"]
