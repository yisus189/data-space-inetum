.PHONY: help install dev test lint clean up down logs migration migrate shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e .[dev]

dev: ## Run development server locally
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	pytest -v

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

lint: ## Check code style
	python -m py_compile src/**/*.py tests/**/*.py

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage

up: ## Start all services with docker-compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

migration: ## Create a new migration
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate: ## Run migrations
	alembic upgrade head

migrate-down: ## Rollback last migration
	alembic downgrade -1

shell: ## Open a shell in the API container
	docker-compose exec api /bin/bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec db psql -U dataspace_user -d dataspace

quickstart: ## Run quickstart script
	./quickstart.sh

build: ## Build docker images
	docker-compose build

restart: ## Restart all services
	docker-compose restart

restart-api: ## Restart API service
	docker-compose restart api

status: ## Show status of all services
	docker-compose ps

token-provider: ## Get token for provider user
	@curl -s -X POST http://localhost:8080/realms/dataspace/protocol/openid-connect/token \
		-H "Content-Type: application/x-www-form-urlencoded" \
		-d "username=provider-user" \
		-d "password=provider123" \
		-d "grant_type=password" \
		-d "client_id=dataspace-api" \
		-d "client_secret=dataspace-secret" | jq -r '.access_token'

token-consumer: ## Get token for consumer user
	@curl -s -X POST http://localhost:8080/realms/dataspace/protocol/openid-connect/token \
		-H "Content-Type: application/x-www-form-urlencoded" \
		-d "username=consumer-user" \
		-d "password=consumer123" \
		-d "grant_type=password" \
		-d "client_id=dataspace-api" \
		-d "client_secret=dataspace-secret" | jq -r '.access_token'
