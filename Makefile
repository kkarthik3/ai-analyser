# ============================================================
# AI-Bot Options Intelligence Platform — Makefile
# ============================================================

.PHONY: help dev prod stop restart logs migrate test lint clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- Docker ----

dev: ## Start all services in dev mode (hot reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

prod: ## Start all services in production mode
	docker compose up --build -d

stop: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose down && docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

logs: ## Tail logs for all services
	docker compose logs -f

logs-backend: ## Tail backend logs
	docker compose logs -f backend

logs-celery: ## Tail celery worker logs
	docker compose logs -f celery-worker

# ---- Database ----

migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-downgrade: ## Downgrade last migration
	docker compose exec backend alembic downgrade -1

db-shell: ## Open psql shell
	docker compose exec postgres psql -U aibot -d options_intel

# ---- Testing ----

test: ## Run all backend tests
	docker compose exec backend pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	docker compose exec backend pytest tests/unit -v --tb=short

test-cov: ## Run tests with coverage
	docker compose exec backend pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# ---- Code Quality ----

lint: ## Run linters
	docker compose exec backend ruff check app/
	docker compose exec backend mypy app/ --ignore-missing-imports

format: ## Format code
	docker compose exec backend ruff format app/

# ---- Cleanup ----

clean: ## Remove all containers, volumes, and build artifacts
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

# ---- Utility ----

shell-backend: ## Open a shell in the backend container
	docker compose exec backend bash

shell-frontend: ## Open a shell in the frontend container
	docker compose exec frontend sh

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli
