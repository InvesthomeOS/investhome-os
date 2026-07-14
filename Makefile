.PHONY: help install dev build up down logs api-test migrate format

help:
	@echo "Investhome OS — available targets:"
	@echo "  install    Install JS and Python dependencies"
	@echo "  dev        Start local dev servers (turbo)"
	@echo "  build      Build all workspace packages"
	@echo "  up         Start Docker Compose stack"
	@echo "  down       Stop Docker Compose stack"
	@echo "  logs       Tail Docker Compose logs"
	@echo "  api-test   Run API test suite"
	@echo "  migrate    Apply database migrations"
	@echo "  format     Format repository sources"

install:
	pnpm install
	cd apps/api && pip install -e ".[dev]"

dev:
	pnpm dev

build:
	pnpm build

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

api-test:
	cd apps/api && pytest

migrate:
	cd apps/api && alembic upgrade head

format:
	pnpm format
