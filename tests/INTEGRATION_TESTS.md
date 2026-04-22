# FastAPI Integration Tests

This directory contains integration tests for the FastAPI backend endpoints.

## Overview

The integration test suite covers critical happy-path scenarios for:
- **Health checks** (`GET /healthz`)
- **Authentication** (`POST /api/v1/auth/token`)
- **Config CRUD** (create, read, update, delete cloud configurations)
- **Config testing** (`POST /api/v1/config/{id}/test`)
- **Extractor runs** (start, status, cancel)
- **Authorization** (auth-required endpoints)

## Test Files

- **`test_api_integration.py`** — Core integration tests for all FastAPI routes
- **`conftest.py`** — Pytest fixtures (client, auth_client, mock DB)

## Test Structure

Tests use `pytest` with the `@pytest.mark.integration` marker:

```bash
# Run all integration tests
pytest tests/ -m integration

# Run specific test class
pytest tests/test_api_integration.py::TestAuthToken -v

# Run tests excluding integration tests
pytest tests/ -m "not integration"
```

## Setup

1. **Install dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Database (optional):** 
   - Tests use mocked DB connections by default
   - For real DB testing, set `PG_DSN` environment variable:
     ```bash
     export PG_DSN="postgresql://user:pass@localhost/testdb"
     ```

3. **Run tests:**
   ```bash
   pytest tests/test_api_integration.py -v
   ```

## Test Coverage

### Healthz Tests
- `test_healthz_returns_200_ok` — Health endpoint returns 200 OK status
- `test_healthz_includes_database_status` — Database status is included

### Auth Tests
- `test_login_success_with_valid_credentials` — Valid credentials return JWT token
- `test_login_fails_with_invalid_credentials` — Invalid password returns 401
- `test_login_fails_with_nonexistent_user` — Nonexistent user returns 401
- `test_login_fails_with_disabled_account` — Disabled account returns 403

### Config CRUD Tests
- `test_create_config_success` — Creating config returns 201 with config ID
- `test_list_configs_success` — Listing configs returns array
- `test_get_config_by_id_success` — Getting specific config by ID
- `test_get_config_not_found` — Nonexistent config returns 404
- `test_update_config_success` — Updating config returns updated data
- `test_delete_config_success` — Deleting config returns 204

### Config Test Endpoint
- `test_config_test_gcp_success` — Testing GCP credentials succeeds
- `test_config_test_azure_success` — Testing Azure credentials succeeds
- `test_config_test_not_found` — Testing nonexistent config returns 404

### Extractor Tests
- `test_run_extractor_success` — Running extractor returns run ID
- `test_run_extractor_requires_config_id` — Missing config_id returns 400
- `test_list_extractors_status_success` — Listing extractor runs succeeds
- `test_list_extractors_status_empty` — Empty runs list returns 0 count
- `test_get_extractor_run_success` — Getting run by ID succeeds
- `test_get_extractor_run_not_found` — Nonexistent run returns 404
- `test_cancel_extractor_run_success` — Canceling run succeeds
- `test_cancel_extractor_run_not_found` — Canceling nonexistent run returns 404

### Auth-Required Endpoints
- `test_config_list_requires_auth` — Listing configs without token returns 401
- `test_extractor_run_requires_auth` — Running extractor without token returns 401
- `test_healthz_does_not_require_auth` — Healthz endpoint is public
- `test_auth_token_does_not_require_auth` — Token endpoint is public

## Fixtures

### `client`
A `TestClient` with mocked DB connections. Used for testing unauthenticated endpoints and auth failure scenarios.

```python
def test_something(client):
    response = client.get("/healthz")
    assert response.status_code == 200
```

### `auth_client`
A `TestClient` that automatically includes JWT token in all requests. Used for testing protected endpoints.

```python
def test_protected_endpoint(auth_client):
    response = auth_client.get("/api/v1/config")
    assert response.status_code == 200
```

## Mocking Strategy

Tests use `unittest.mock.patch` to mock database and external service calls:

```python
with patch("api.db.query_one") as mock_query:
    mock_query.return_value = {"id": "1", "username": "admin"}
    # test code here
```

This approach ensures tests:
- Run without real DB connectivity
- Don't depend on external services (Azure, GCP)
- Execute quickly
- Are deterministic

## Running in CI/CD

The GitHub Actions workflow runs integration tests:

```bash
pytest tests/test_api_integration.py -v --tb=short -m integration
```

Tests are marked with `@pytest.mark.integration` so they can be selectively run or skipped:

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"
```

## Common Issues

**ImportError: No module named 'api'**
- Ensure `PYTHONPATH` includes the backend directory
- The conftest.py automatically sets up the path, but you can also set it manually:
  ```bash
  export PYTHONPATH=/path/to/finna-app/backend/app:$PYTHONPATH
  pytest tests/
  ```

**Database connection errors during mocked tests**
- These should not occur — if they do, check that all `api.db` calls are properly patched
- Look for missing patches in test code

**Token validation errors**
- Ensure `JWT_SECRET` environment variable matches conftest.py value
- The conftest sets `JWT_SECRET="test-secret-key"` by default

## Adding New Tests

When adding tests for new endpoints:

1. Create a new test class in `test_api_integration.py`:
   ```python
   class TestMyNewEndpoint:
       @pytest.mark.integration
       def test_my_happy_path(self, auth_client):
           with patch("api.db.query_one") as mock:
               mock.return_value = {"id": "123"}
               response = auth_client.post("/api/v1/my-endpoint")
               assert response.status_code == 200
   ```

2. Use descriptive test names following the pattern: `test_{what}_{expected_result}`

3. Mock all external dependencies (DB, cloud providers)

4. Test happy path first, then error cases (400, 401, 404, etc.)

5. Use the `auth_client` fixture for protected endpoints

## See Also

- [API Documentation](../backend/README.md)
- [Database Schema](../sql/init_docker.sql)
- [Pytest Documentation](https://docs.pytest.org/)
