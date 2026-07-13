# IntelliDesk AI — Developer Makefile

.PHONY: help build up down logs restart migrate seed test lint shell clean

# ─── Colors ───────────────────────────────────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help message
	@echo ""
	@echo " IntelliDesk AI — Developer Commands"
	@echo " ══════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Docker ───────────────────────────────────────────────────────────────────
build: ## Build all Docker images
	docker-compose build

up: ## Start all services in background
	docker-compose up -d
	@echo "$(GREEN)✅ Services started. API: http://localhost:8000$(RESET)"
	@echo "   Flower: http://localhost:5555"

down: ## Stop and remove all containers
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Tail logs for all services
	docker-compose logs -f

logs-backend: ## Tail backend logs only
	docker-compose logs -f backend

logs-worker: ## Tail Celery worker logs only
	docker-compose logs -f celery_worker

ps: ## Show running containers and status
	docker-compose ps

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run Alembic database migrations
	docker-compose exec backend flask db upgrade
	@echo "$(GREEN)✅ Migrations applied.$(RESET)"

migrate-create: ## Create a new migration (usage: make migrate-create msg="add ticket table")
	docker-compose exec backend flask db migrate -m "$(msg)"

migrate-rollback: ## Rollback one migration
	docker-compose exec backend flask db downgrade -1

seed: ## Seed database with roles, departments, and demo users
	docker-compose exec backend flask seed-db
	@echo "$(GREEN)✅ Database seeded.$(RESET)"
	@echo "   Admin: admin@intellidesk.ai / Admin@123!"

reset-db: ## Drop and recreate database (WARNING: destroys all data)
	docker-compose exec backend flask drop-db
	docker-compose exec backend flask db upgrade
	docker-compose exec backend flask seed-db
	@echo "$(GREEN)✅ Database reset and reseeded.$(RESET)"

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run full test suite with coverage
	docker-compose exec backend pytest tests/ --cov=app --cov-report=term-missing -v

test-unit: ## Run unit tests only
	docker-compose exec backend pytest tests/unit/ -v

test-integration: ## Run integration tests only
	docker-compose exec backend pytest tests/integration/ -v

test-file: ## Run a specific test file (usage: make test-file f=tests/integration/test_auth_api.py)
	docker-compose exec backend pytest $(f) -v

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run all linters (flake8, black, isort)
	docker-compose exec backend flake8 .
	docker-compose exec backend black . --check
	docker-compose exec backend isort . --check-only
	@echo "$(GREEN)✅ All linters passed.$(RESET)"

format: ## Auto-format code with black and isort
	docker-compose exec backend black .
	docker-compose exec backend isort .
	@echo "$(GREEN)✅ Code formatted.$(RESET)"

# ─── Development ──────────────────────────────────────────────────────────────
shell: ## Open Flask Python shell
	docker-compose exec backend flask shell

bash: ## Open bash shell in backend container
	docker-compose exec backend bash

install: ## Install Python dependencies (local dev without Docker)
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

# ─── Full Setup ───────────────────────────────────────────────────────────────
setup: build up ## Build, start, migrate, and seed in one command
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo ""
	@echo "$(GREEN)🚀 IntelliDesk AI is ready!$(RESET)"
	@echo "   API:    http://localhost:8000/api/v1"
	@echo "   Health: http://localhost:8000/api/v1/health"
	@echo "   Flower: http://localhost:5555"
	@echo ""
	@echo "   Admin: admin@intellidesk.ai / Admin@123!"

clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi local
	@echo "$(GREEN)✅ All containers and volumes removed.$(RESET)"
