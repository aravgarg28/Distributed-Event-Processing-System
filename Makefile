.PHONY: up down logs clean status build test

COMPOSE  := docker compose -f infrastructure/docker-compose.yml
BUILD_DIR := build

# ---------------------------------------------------------------------------
# Docker Compose — infrastructure stack
# ---------------------------------------------------------------------------

# Start all services in detached mode
up:
	$(COMPOSE) up -d

# Stop and remove containers (volumes preserved)
down:
	$(COMPOSE) down

# Tail logs for all services; pass SERVICE=<name> to filter, e.g. make logs SERVICE=kafka
logs:
	$(COMPOSE) logs -f $(SERVICE)

# Full reset: stop containers and delete all named volumes
clean:
	$(COMPOSE) down -v

# Show current container status
status:
	$(COMPOSE) ps

# ---------------------------------------------------------------------------
# Local C++ build (requires grpc, protobuf, rdkafka dev packages installed)
# ---------------------------------------------------------------------------

# Configure + build the ingress_server binary
build:
	cmake -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=OFF
	cmake --build $(BUILD_DIR) --target ingress_server -j$$(nproc)

# Build everything including tests, then run the test suite
test:
	cmake -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
	cmake --build $(BUILD_DIR) -j$$(nproc)
	cd $(BUILD_DIR) && ctest --output-on-failure
