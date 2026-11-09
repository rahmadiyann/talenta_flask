# Makefile for Talenta API Docker

.PHONY: help build up down restart logs clean clockin clockout shell test config panel api-health

# Variables
IMAGE_NAME := talenta-api
CONTAINER_NAME := talenta-scheduler
COMPOSE := docker compose
DOCKER := docker

# Default target
.DEFAULT_GOAL := help

# Positional time argument support: `make clockin 08:45` (also accepts TIME=08:45).
# Any extra goals that aren't real targets are treated as the time value.
CLOCK_POS_ARGS := $(filter-out clockin clockout,$(MAKECMDGOALS))
CLOCK_TIME := $(if $(TIME),$(TIME),$(CLOCK_POS_ARGS))

help: ## Show this help message
	@echo "Talenta API - Docker Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	@echo "🏗️  Building Docker image..."
	$(COMPOSE) build

up: ## Start the scheduler in background
	@echo "🚀 Starting scheduler..."
	$(COMPOSE) up talenta-scheduler
	@echo "✅ Scheduler started! Use 'make logs' to view output"

up-d: ## Start the scheduler in background
	@echo "🚀 Starting scheduler..."
	$(COMPOSE) up -d talenta-scheduler
	@echo "✅ Scheduler started! Use 'make logs' to view output"

down: ## Stop and remove containers
	@echo "🛑 Stopping containers..."
	$(COMPOSE) down

restart: down up ## Restart the scheduler

logs: ## View scheduler logs (follow mode)
	@echo "📋 Viewing logs (Ctrl+C to exit)..."
	$(COMPOSE) logs -f talenta-scheduler

logs-tail: ## View last 50 lines of logs
	$(COMPOSE) logs --tail=50 talenta-scheduler

status: ## Show container status
	@echo "📊 Container status:"
	$(COMPOSE) ps

clockin: ## Execute clock in, detached. Pass a time: make clockin 08:45 (or 08.45 / 0845)
	@echo "⏰ Starting clock in$(if $(CLOCK_TIME), at $(CLOCK_TIME),) (detached)..."
	@$(COMPOSE) run -d --rm talenta-clockin clockin $(CLOCK_TIME)
	@echo "✅ Running in background. Safe to close the terminal. Check: docker ps / docker logs <id>"

clockout: ## Execute clock out, detached. Pass a time: make clockout 18:15 (or 18.15 / 1815)
	@echo "⏰ Starting clock out$(if $(CLOCK_TIME), at $(CLOCK_TIME),) (detached)..."
	@$(COMPOSE) run -d --rm talenta-clockout clockout $(CLOCK_TIME)
	@echo "✅ Running in background. Safe to close the terminal. Check: docker ps / docker logs <id>"

# Swallow the positional time argument so make doesn't error with "No rule to make target".
# Only matches goals that have no real rule (e.g. 08:45, 0845), turning them into no-ops.
%::
	@:

shell: ## Open a shell in the container
	@echo "🐚 Opening shell..."
	$(COMPOSE) run --rm talenta-scheduler bash

exec-shell: ## Open a shell in running container
	@echo "🐚 Opening shell in running container..."
	$(DOCKER) exec -it $(CONTAINER_NAME) /bin/bash

test: ## Test configuration
	@echo "🧪 Testing configuration..."
	$(COMPOSE) run --rm talenta-scheduler python3 -c "from src.config import config_local; print('✅ Config OK')"

config: ## Show current configuration
	@echo "📝 Current configuration:"
	@$(COMPOSE) run --rm talenta-scheduler python3 -c "from src.config import config_local as c; print(f'Email: {c.EMAIL}'); print(f'Location: {c.LATITUDE}, {c.LONGITUDE}'); print(f'Clock In: {c.TIME_CLOCK_IN}'); print(f'Clock Out: {c.TIME_CLOCK_OUT}')"

# Admin panel
PORT ?= 5000

panel: ## Print the admin panel URL
	@echo "🖥️  Admin panel: http://localhost:$(PORT)"
	@echo "   Log in with ADMIN_PASSWORD, then manage accounts, schedules and clock in/out."

api-health: ## Check web API health
	@echo "🏥 Checking API health..."
	@curl http://localhost:$(PORT)/health -s | python3 -m json.tool || echo "❌ Failed to connect. Is the scheduler running?"

# NOTE: enable/disable/clock in/out and schedules are now managed per-account
# from the admin panel (http://localhost:$(PORT)) behind the ADMIN_PASSWORD login,
# not via unauthenticated curl endpoints. Use `make clockin` / `make clockout` for
# the one-shot CLI (env-configured account), or the panel for everything else.

clean: ## Remove containers, images, and volumes
	@echo "🧹 Cleaning up..."
	$(COMPOSE) down -v --rmi all --remove-orphans
	@echo "✅ Cleanup complete"

rebuild: clean build ## Clean rebuild from scratch

# Docker native commands (without docker compose)
docker-build: ## Build image using docker (no compose)
	@echo "🏗️  Building Docker image..."
	$(DOCKER) build -t $(IMAGE_NAME):latest .

docker-run-scheduler: ## Run scheduler using docker (no compose)
	@echo "🚀 Starting scheduler..."
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-v $(PWD)/src/config/config_local.py:/app/src/config/config_local.py:ro \
		$(IMAGE_NAME):latest scheduler

docker-run-clockin: ## Clock in using docker (no compose)
	@echo "⏰ Executing clock in..."
	$(DOCKER) run --rm \
		-v $(PWD)/src/config/config_local.py:/app/src/config/config_local.py:ro \
		$(IMAGE_NAME):latest clockin

docker-run-clockout: ## Clock out using docker (no compose)
	@echo "⏰ Executing clock out..."
	$(DOCKER) run --rm \
		-v $(PWD)/src/config/config_local.py:/app/src/config/config_local.py:ro \
		$(IMAGE_NAME):latest clockout

docker-stop: ## Stop container using docker (no compose)
	@echo "🛑 Stopping container..."
	$(DOCKER) stop $(CONTAINER_NAME) || true
	$(DOCKER) rm $(CONTAINER_NAME) || true

docker-logs: ## View logs using docker (no compose)
	$(DOCKER) logs -f $(CONTAINER_NAME)

# Development targets
dev-setup: ## Setup development environment with uv
	@echo "🔧 Setting up development environment..."
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

dev-sync: ## Sync dependencies with uv
	@echo "🔄 Syncing dependencies with uv..."
	@uv pip sync pyproject.toml

dev-lock: ## Create/update uv.lock file
	@echo "🔒 Creating/updating uv.lock..."
	@uv pip compile pyproject.toml -o requirements.lock

dev-install: ## Install dependencies with uv
	@echo "📦 Installing dependencies with uv..."
	@uv pip install -r pyproject.toml

dev-install-dev: ## Install dev dependencies with uv
	@echo "📦 Installing dev dependencies with uv..."
	@uv pip install -r pyproject.toml --extra dev

dev-test: ## Run tests in development mode
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ || echo "⚠️  No tests found"

# Quick actions
start: up ## Alias for 'up'
stop: down ## Alias for 'down'
log: logs ## Alias for 'logs'

# Version info
version: ## Show version information
	@echo "Talenta API - Docker Version"
	@echo "Docker version:"
	@$(DOCKER) --version
	@echo "Docker Compose version:"
	@$(COMPOSE) --version
	@echo "Image: $(IMAGE_NAME):latest"
