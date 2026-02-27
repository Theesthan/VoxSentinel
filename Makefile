.PHONY: build run stop test-unit test-integration test-e2e lint format migrate seed venv

# ── Virtual environment (single root-level venv) ──
venv:
	python -m venv .venv
	.venv/Scripts/pip install --upgrade pip setuptools wheel
	.venv/Scripts/pip install pydantic pydantic-settings "sqlalchemy[asyncio]" asyncpg alembic redis celery structlog prometheus-client numpy fastapi uvicorn httpx pytest pytest-asyncio pytest-cov pytest-mock ruff mypy
	.venv/Scripts/pip install -e packages/tg-common --no-deps
	.venv/Scripts/pip install -e services/ingestion --no-deps
	.venv/Scripts/pip install -e services/vad --no-deps

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

test-unit:
	.venv/Scripts/python -m pytest --rootdir=. -c pyproject.toml -v --cov --cov-report=term-missing

test-integration:
	.venv/Scripts/python -m pytest tests/integration/ -v --cov --cov-report=term-missing

test-e2e:
	.venv/Scripts/python -m pytest tests/e2e/ -v

lint:
	ruff check .
	mypy services/ packages/

format:
	ruff format .

migrate:
	alembic -c packages/tg-common/src/tg_common/db/migrations/alembic.ini upgrade head

seed:
	python scripts/seed_db.py
