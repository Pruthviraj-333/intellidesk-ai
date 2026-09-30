# IntelliDesk AI — Developer Makefile

.PHONY: help build up down logs logs-backend logs-worker logs-beat logs-flower restart ps \
        migrate migrate-create migrate-rollback seed reset-db \
        test test-unit test-integration test-file \
        lint format shell bash \
        frontend-install frontend-dev frontend-build frontend-lint frontend-test \
        install install-backend setup clean

DOCKER_COMPOSE ?= docker compose

# ─── Colors ───────────────────────────────────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help message
	@echo ""
	@echo " IntelliDesk AI — Developer Commands"
	@echo " ======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Docker ───────────────────────────────────────────────────────────────────
build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

up: ## Start all services in background
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)[OK] Services started.$(RESET)"
	@echo "   Frontend: http://localhost (via NGINX) or http://localhost:5173"
	@echo "   API:      http://localhost:8000/api/v1"
	@echo "   Docs:     http://localhost:8000/api/v1/docs"
	@echo "   Flower:   http://localhost:5555"

down: ## Stop and remove all containers
	$(DOCKER_COMPOSE) down

restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

logs: ## Tail logs for all services
	$(DOCKER_COMPOSE) logs -f

logs-backend: ## Tail backend logs only
	$(DOCKER_COMPOSE) logs -f backend

logs-worker: ## Tail Celery worker logs only
	$(DOCKER_COMPOSE) logs -f celery_worker

logs-beat: ## Tail Celery beat logs only
	$(DOCKER_COMPOSE) logs -f celery_beat

logs-flower: ## Tail Celery Flower logs only
	$(DOCKER_COMPOSE) logs -f flower

ps: ## Show running containers and status
	$(DOCKER_COMPOSE) ps

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run Alembic database migrations
	$(DOCKER_COMPOSE) exec backend flask db upgrade
	@echo "$(GREEN)[OK] Migrations applied.$(RESET)"

migrate-create: ## Create a new migration (usage: make migrate-create msg="add ticket table")
	$(DOCKER_COMPOSE) exec backend flask db migrate -m "$(msg)"

migrate-rollback: ## Rollback one migration
	$(DOCKER_COMPOSE) exec backend flask db downgrade -1

seed: ## Seed database with roles, departments, and demo users
	$(DOCKER_COMPOSE) exec backend flask seed-db
	@echo "$(GREEN)[OK] Database seeded.$(RESET)"
	@echo "   Admin: admin@intellidesk.ai / Admin@123!"

reset-db: ## Drop and recreate database (WARNING: destroys all data)
	$(DOCKER_COMPOSE) exec backend flask drop-db --yes
	$(DOCKER_COMPOSE) exec backend flask db upgrade
	$(DOCKER_COMPOSE) exec backend flask seed-db
	@echo "$(GREEN)[OK] Database reset and reseeded.$(RESET)"

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run full test suite with coverage
	$(DOCKER_COMPOSE) exec backend pytest tests/ --cov=app --cov-report=term-missing -v

test-unit: ## Run unit tests only
	$(DOCKER_COMPOSE) exec backend pytest tests/unit/ -v

test-integration: ## Run integration tests only
	$(DOCKER_COMPOSE) exec backend pytest tests/integration/ -v

test-file: ## Run a specific test file (usage: make test-file f=tests/integration/test_auth_api.py)
	$(DOCKER_COMPOSE) exec backend pytest $(f) -v

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run all Python linters (flake8, black, isort)
	$(DOCKER_COMPOSE) exec backend flake8 .
	$(DOCKER_COMPOSE) exec backend black . --check
	$(DOCKER_COMPOSE) exec backend isort . --check-only
	@echo "$(GREEN)[OK] All linters passed.$(RESET)"

format: ## Auto-format Python code with black and isort
	$(DOCKER_COMPOSE) exec backend black .
	$(DOCKER_COMPOSE) exec backend isort .
	@echo "$(GREEN)[OK] Code formatted.$(RESET)"

# ─── Frontend ─────────────────────────────────────────────────────────────────
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start frontend development server
	cd frontend && npm run dev

frontend-build: ## Build frontend production bundle
	cd frontend && npm run build

frontend-lint: ## Run frontend linter (oxlint)
	cd frontend && npm run lint

frontend-test: ## Run frontend test suite (vitest)
	cd frontend && npm run test

# ─── Development & Shell ──────────────────────────────────────────────────────
shell: ## Open Flask Python shell
	$(DOCKER_COMPOSE) exec backend flask shell

bash: ## Open bash shell in backend container
	$(DOCKER_COMPOSE) exec backend bash

install-backend: ## Install Python dependencies for local development
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

install: install-backend frontend-install ## Install all dependencies (backend + frontend)

# ─── Full Setup ───────────────────────────────────────────────────────────────
setup: build up ## Build, start, migrate, and seed in one command
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo ""
	@echo "$(GREEN)[READY] IntelliDesk AI is ready!$(RESET)"
	@echo "   Frontend: http://localhost"
	@echo "   API:      http://localhost:8000/api/v1"
	@echo "   Health:   http://localhost:8000/api/v1/health"
	@echo "   Flower:   http://localhost:5555"
	@echo ""
	@echo "   Admin:    admin@intellidesk.ai / Admin@123!"

clean: ## Remove all containers, volumes, and images
	$(DOCKER_COMPOSE) down -v --rmi local
	@echo "$(GREEN)[OK] All containers and volumes removed.$(RESET)"
