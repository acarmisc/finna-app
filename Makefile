.PHONY: migrate migrate-rollback migrate-create

migrate:
	alembic upgrade head

migrate-rollback:
	alembic downgrade -1

migrate-create:
	@test "$(msg)" || (echo "Usage: make migrate-create msg=\"description\"" && exit 1)
	alembic revision --autogenerate -m "$(msg)"