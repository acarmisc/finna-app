# Local Development Setup

This guide covers setting up a full local environment for Finna development.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- `uv` (recommended for Python package management)

## 1. Backend Setup

### Environment Variables
Create a `.env` file in the root directory (or export them):

```bash
PG_DSN="postgresql://finops:finops_dev@localhost:5432/finops"
SECRET_KEY="your-super-secret-key"
```

### Database
Start the PostgreSQL container:
```bash
docker-compose up -d postgres
```

Run migrations:
```bash
make migrate
```

### Seed Data
To populate the database with realistic sample data for UI development:
```bash
make seed
```

### Run API
```bash
uv run python -m uvicorn api.main:app --port 8000 --reload
```

## 2. Frontend Setup

The frontend is built with React and Vite.

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```
The dev server runs on `http://localhost:5173` and proxies `/api` requests to `http://localhost:8000`.

## 3. Common Makefile Commands

| Command | Description |
|---------|-------------|
| `make migrate` | Apply all database migrations |
| `make migrate-create msg="description"` | Create a new migration file |
| `make migrate-rollback` | Rollback the last migration |
| `make seed` | Load sample data from `fixtures/sample_data.json` |

## 4. Testing

### Backend Tests
```bash
pytest
```

### Frontend Type Checking
```bash
npx tsc --noEmit
```

### Smoke Test
Runs a full E2E check of the containerized stack:
```bash
bash scripts/smoke-test.sh
```
