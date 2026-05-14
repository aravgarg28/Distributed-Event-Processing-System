.PHONY: up down logs clean status

COMPOSE := docker compose -f infrastructure/docker-compose.yml

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
