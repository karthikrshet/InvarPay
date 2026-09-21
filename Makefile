# InvarPay AI — Makefile
# Requires: Docker, Python 3.11+, pnpm, uv (or pip)

.PHONY: help dev stop logs setup migrate seed demo test test-unit test-integration test-e2e test-chaos test-security lint type-check clean

COMPOSE = docker compose -f infra/docker/docker-compose.yml
PYTHON = python
UV = uv

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- Environment setup ----

setup: ## First-time setup: copy .env, install deps, start services, migrate, seed
	@if not exist .env (copy .env.example .env && echo "[INFO] .env created from .env.example — fill in your values")
	$(UV) pip install -e ".[dev]" 2>nul || pip install -e ".[dev]"
	pnpm install
	$(COMPOSE) up -d postgres redis
	@echo "[INFO] Waiting for Postgres to be ready..."
	@timeout /t 5 /nobreak >nul
	$(MAKE) migrate
	$(MAKE) seed
	@echo "[OK] Setup complete. Run 'make dev' to start all services."

# ---- Dev server ----

dev: ## Start all services (API, Worker, Web, Postgres, Redis)
	$(COMPOSE) up --build

dev-api: ## Start only API + dependencies
	$(COMPOSE) up --build api postgres redis

stop: ## Stop all services
	$(COMPOSE) down

logs: ## Tail all service logs
	$(COMPOSE) logs -f

# ---- Database ----

migrate: ## Run all Alembic migrations
	$(PYTHON) -m alembic -c apps/api/alembic.ini upgrade head

migrate-down: ## Roll back last migration
	$(PYTHON) -m alembic -c apps/api/alembic.ini downgrade -1

migrate-history: ## Show migration history
	$(PYTHON) -m alembic -c apps/api/alembic.ini history

seed: ## Seed synthetic demo data (clearly labelled)
	$(PYTHON) examples/demo-merchant/seed.py

# ---- Demo ----

demo: dev seed ## Start full stack and run demo scenario
	@echo ""
	@echo "============================================"
	@echo " InvarPay AI Demo"
	@echo " Dashboard: http://localhost:3000"
	@echo " API docs:  http://localhost:8000/docs"
	@echo " API:       http://localhost:8000"
	@echo "============================================"
	$(PYTHON) examples/demo-merchant/run_demo.py

# ---- Tests ----

test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v

test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit/ -v

test-integration: ## Run integration tests (requires running Postgres + Redis)
	$(PYTHON) -m pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	$(PYTHON) -m pytest tests/e2e/ -v

test-chaos: ## Run chaos/resilience tests
	$(PYTHON) -m pytest tests/chaos/ -v

test-security: ## Run security isolation tests
	$(PYTHON) -m pytest tests/security/ -v

test-evals: ## Run agent evaluation suite
	$(PYTHON) -m pytest tests/evals/ -v

# ---- Code quality ----

lint: ## Run ruff linter + eslint
	$(PYTHON) -m ruff check apps/ modules/ tests/ integrations/
	cd apps/web && pnpm lint

lint-fix: ## Auto-fix lint issues
	$(PYTHON) -m ruff check --fix apps/ modules/ tests/ integrations/

type-check: ## Run mypy + tsc
	$(PYTHON) -m mypy apps/api/app modules/ --ignore-missing-imports
	cd apps/web && pnpm tsc --noEmit

format: ## Format Python + TypeScript code
	$(PYTHON) -m ruff format apps/ modules/ tests/
	cd apps/web && pnpm prettier --write .

# ---- Cleanup ----

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	cd apps/web && rm -rf .next out 2>/dev/null || true
	@echo "Clean complete."
