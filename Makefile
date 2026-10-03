# Shortcuts for the Docker workflow. Run `make help` for the list.
.DEFAULT_GOAL := help
COMPOSE := docker compose

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Start the dev stack (UI :5173, API :8000)
	$(COMPOSE) up --build -d
	@echo "UI:  http://localhost:5173"
	@echo "API: http://localhost:8000/api/docs"

down: ## Stop the dev stack (data volumes are kept)
	$(COMPOSE) down

reset: ## Stop the dev stack and DELETE its database + uploaded files
	$(COMPOSE) down -v

logs: ## Follow logs of all services
	$(COMPOSE) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE) ps

test: ## Run backend + frontend tests inside the containers
	$(COMPOSE) run --rm --no-deps api pytest
	$(COMPOSE) run --rm --no-deps web npm test

lint: ## Lint backend + frontend inside the containers
	$(COMPOSE) run --rm --no-deps api ruff check .
	$(COMPOSE) run --rm --no-deps web sh -c "npm run lint && npm run typecheck"

migration: ## Create a new Alembic migration: make migration m="add column x"
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

prod-up: ## Start the production-like stack on :8080
	$(COMPOSE) -f docker-compose.prod.yml up --build -d
	@echo "App: http://localhost:8080"

prod-down: ## Stop the production-like stack
	$(COMPOSE) -f docker-compose.prod.yml down

.PHONY: help up down reset logs ps test lint migration prod-up prod-down
