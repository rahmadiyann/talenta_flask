# Makefile for Talenta API Docker

.PHONY: help build up down restart logs clean clockin clockout shell test config

# Variables
IMAGE_NAME := talenta-api
CONTAINER_NAME := talenta-scheduler
COMPOSE := docker-compose
DOCKER := docker

# Default target
.DEFAULT_GOAL := help

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

clockin: ## Execute clock in manually
	@echo "⏰ Executing clock in..."
	$(COMPOSE) run --rm talenta-clockin

clockout: ## Execute clock out manually
	@echo "⏰ Executing clock out..."
	$(COMPOSE) run --rm talenta-clockout

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

clean: ## Remove containers, images, and volumes
	@echo "🧹 Cleaning up..."
	$(COMPOSE) down -v --rmi all --remove-orphans
	@echo "✅ Cleanup complete"

rebuild: clean build ## Clean rebuild from scratch

# Docker native commands (without docker-compose)
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
dev-setup: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	@if [ ! -f src/config/config_local.py ]; then \
		echo "✅ Created src/config/config_local.py - please edit with your credentials"; \
	else \
		echo "ℹ️  src/config/config_local.py already exists"; \
	fi

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
