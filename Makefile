.PHONY: migrate migrate-rollback migrate-create seed

migrate:
	cd backend && alembic upgrade head

migrate-rollback:
	cd backend && alembic downgrade -1

migrate-create:
	@test "$(msg)" || (echo "Usage: make migrate-create msg=\"description\"" && exit 1)
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	python3 scripts/seed.py

build-frontend:
	cd frontend && npm run build

dev-frontend:
	cd frontend && npm run dev

run-api:
	uv run python -m uvicorn backend.app.main:app --port 8000 --reload