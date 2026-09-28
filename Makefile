.PHONY: dev gen-api hooks-install lint format-check typecheck test build benchmark check

dev:
	@set -m; \
	(cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) & backend_pid=$$!; \
	(cd frontend && exec ./node_modules/.bin/vite --host 127.0.0.1) & frontend_pid=$$!; \
	trap 'kill "$$backend_pid" "$$frontend_pid" 2>/dev/null || true' INT TERM EXIT; \
	wait

gen-api:
	@set -eu; trap 'rm -f frontend/.openapi.json' EXIT; \
	(cd backend && uv run python -m scripts.export_openapi ../frontend/.openapi.json); \
	(cd frontend && npm run gen:api)

hooks-install:
	uv run --project backend pre-commit install

lint:
	cd backend && uv run ruff check app scripts tests
	npm --prefix frontend run lint

format-check:
	cd backend && uv run ruff format --check app scripts tests
	npm --prefix frontend run format:check

typecheck:
	cd backend && uv run mypy app scripts tests
	npm --prefix frontend run build

test:
	cd backend && uv run pytest
	npm --prefix frontend test

build:
	npm --prefix frontend run build

benchmark:
	cd backend && uv run python scripts/benchmark_models.py

check: lint format-check typecheck test
