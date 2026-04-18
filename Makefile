.PHONY: migrate migrate-rollback migrate-create seed

migrate:
	alembic upgrade head

migrate-rollback:
	alembic downgrade -1

migrate-create:
	@test "$(msg)" || (echo "Usage: make migrate-create msg=\"description\"" && exit 1)
	alembic revision --autogenerate -m "$(msg)"

seed:
	python3 scripts/seed.py