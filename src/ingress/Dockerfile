# Build context: project root (docker compose uses context: .)
# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# git is required by CMake FetchContent to clone prometheus-cpp at configure time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler \
    protobuf-compiler-grpc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy CMakeLists first so FetchContent (prometheus-cpp clone) is cached in its
# own layer and is not re-run every time source files change.
COPY src/ingress/CMakeLists.txt src/ingress/CMakeLists.txt
RUN cmake \
        -S src/ingress \
        -B cmake-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF

# Now copy the rest of the source and build the binary.
COPY src/ingress/ src/ingress/
RUN cmake --build cmake-build --target ingress_server -j"$(nproc)"

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

EXPOSE 50051  # gRPC endpoint for event producers
EXPOSE 8080   # Prometheus /metrics scrape endpoint

ENV KAFKA_BROKERS="kafka:29092"
ENV KAFKA_TOPIC="events"
ENV GRPC_LISTEN_ADDRESS="0.0.0.0:50051"
ENV METRICS_ADDRESS="0.0.0.0:8080"

CMD ["./ingress_server"]
