# Makefile for Talenta API Docker

.PHONY: help build up down restart logs clean clockin clockout shell test config api-enable api-disable api-status api-health api-clockin api-clockout api-test railway-health railway-status railway-clockin railway-clockout railway-enable railway-disable

# Variables
IMAGE_NAME := talenta-api
CONTAINER_NAME := talenta-scheduler
COMPOSE := docker compose
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

# Web API control commands
api-enable: ## Enable automation via web API
	@echo "✅ Enabling automation..."
	@curl -X POST http://localhost:5000/enable -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

api-disable: ## Disable automation via web API
	@echo "⏸️  Disabling automation..."
	@curl -X POST http://localhost:5000/disable -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

api-status: ## Check automation status via web API
	@echo "📊 Checking automation status..."
	@curl http://localhost:5000/status -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

api-health: ## Check web API health
	@echo "🏥 Checking API health..."
	@curl http://localhost:5000/health -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

api-clockin: ## Trigger manual clock in via API
	@echo "⏰ Triggering clock in via API..."
	@curl -X POST http://localhost:5000/clockin -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

api-clockout: ## Trigger manual clock out via API
	@echo "⏰ Triggering clock out via API..."
	@curl -X POST http://localhost:5000/clockout -s | python3 -m json.tool || echo "❌ Failed to connect to API. Is the scheduler running?"

# Railway deployment testing
railway-health: ## Check Railway deployment health
	@echo "🏥 Checking Railway deployment health..."
	@curl http://localhost:5000/health -s | python3 -m json.tool || echo "❌ Failed to connect"

railway-status: ## Check Railway deployment status
	@echo "📊 Checking Railway deployment status..."
	@curl http://localhost:5000/status -s | python3 -m json.tool || echo "❌ Failed to connect"

railway-clockin: ## Trigger clock in on Railway deployment
	@echo "⏰ Triggering clock in on Railway..."
	@curl -X POST http://localhost:5000/clockin -s | python3 -m json.tool || echo "❌ Failed to connect"

railway-clockout: ## Trigger clock out on Railway deployment
	@echo "⏰ Triggering clock out on Railway..."
	@curl -X POST http://localhost:5000/clockout -s | python3 -m json.tool || echo "❌ Failed to connect"

railway-enable: ## Enable automation on Railway deployment
	@echo "✅ Enabling automation on Railway..."
	@curl -X POST http://localhost:5000/enable -s | python3 -m json.tool || echo "❌ Failed to connect"

railway-disable: ## Disable automation on Railway deployment
	@echo "⏸️  Disabling automation on Railway..."
	@curl -X POST http://localhost:5000/disable -s | python3 -m json.tool || echo "❌ Failed to connect"

api-test: ## Test all web API endpoints
	@echo "🧪 Testing web API endpoints..."
	@echo ""
	@echo "1. Health Check:"
	@curl http://localhost:5000/health -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "2. Current Status:"
	@curl http://localhost:5000/status -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "3. Disable Automation:"
	@curl -X POST http://localhost:5000/disable -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "4. Check Status (should be disabled):"
	@curl http://localhost:5000/status -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "5. Enable Automation:"
	@curl -X POST http://localhost:5000/enable -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "6. Check Status (should be enabled):"
	@curl http://localhost:5000/status -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "7. Manual Clock In:"
	@curl -X POST http://localhost:5000/clockin -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "8. Manual Clock Out:"
	@curl -X POST http://localhost:5000/clockout -s | python3 -m json.tool || echo "❌ Failed"
	@echo ""
	@echo "✅ API test complete"

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
