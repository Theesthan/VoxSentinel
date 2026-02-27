.PHONY: build run stop test-unit test-integration test-e2e lint format migrate seed

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

test-unit:
	pytest services/*/tests/ packages/tg-common/tests/ -v --cov --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v --cov --cov-report=term-missing

test-e2e:
	pytest tests/e2e/ -v

lint:
	ruff check .
	mypy services/ packages/

format:
	ruff format .

migrate:
	alembic -c packages/tg-common/src/tg_common/db/migrations/alembic.ini upgrade head

seed:
	python scripts/seed_db.py
