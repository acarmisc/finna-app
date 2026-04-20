---
title: "Backend to Frontend MVP Integration"
description: "Complete backend-to-frontend integration for FastAPI + React MVP with JWT auth, optimized for low budget tokens"
category: "software-development"
---

# Backend to Frontend MVP Integration

## Overview

This skill guides you through creating a complete backend-to-frontend integration for a FinOps cost management platform using FastAPI (backend) and React/TypeScript (frontend), with JWT authentication and low budget token optimization.

## When to Use

Use this skill when you need to:
- Replace demo/mock UI with a fully connected backend
- Build an end-to-end MVP for a cloud cost management platform
- Implement JWT authentication with FastAPI backend
- Create comprehensive API endpoints for costs, alerts, and configurations
- Optimize agent usage for low budget token consumption

## Quick Start

### 1. Set Up Backend API

**Create FastAPI routes** in `backend/app/api/routes/`:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/costs")
async def get_costs():
    # Cost data endpoint
    pass

@router.get("/alerts")
async def get_alerts():
    # Alerts endpoint
    pass
```

**Register routes** in `backend/app/api/main.py`:

```python
from api.routes import auth, config, extractors, costs, alerts

app.include_router(costs.router, prefix="/api/v1", tags=["costs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
```

### 2. Create TypeScript API Client

**Create** `backend/frontend/src/services/apiClient.ts`:

- JWT token management with localStorage
- Comprehensive error handling with retry logic
- Type-safe request/response handling
- Automatic token refresh

### 3. Implement React Hooks

**Create** `backend/frontend/src/hooks/useApi.ts` with:
- `useData()` - Generic data fetching
- `useCosts()` - Cost data with filtering
- `useAlerts()` - Alert management
- `useRuns()` - Extractor runs
- `useConnections()` - Configuration management

### 4. Create Components

**Create** `backend/frontend/src/components/common/APIScreen.tsx`:
- Health check wrapper
- Error banner display
- Responsive screen layout

**Create** `backend/frontend/src/components/auth/LoginScreen.tsx`:
- Username/password form
- Token storage
- Redirect after login

## Backend API Endpoints

### Costs API (`/api/v1/costs`)
- `GET /costs` - Get cost records with filtering
- `GET /costs/totals` - Get totals by provider
- `GET /costs/by-sku` - Costs grouped by SKU
- `GET /costs/daily` - Daily cost breakdown

### Alerts API (`/api/v1/alerts`)
- `GET /alerts` - Get alerts with filtering
- `GET /alerts/stats` - Alert statistics
- `GET /alerts/active` - Active firing alerts
- `GET /alerts/health` - Extractor health status

### Authentication (`/api/v1/auth`)
- `POST /auth/token` - Get JWT token
- `GET /auth/logout` - Logout
- JWT validation middleware on all protected routes

## Frontend Integration

### Dependencies to Install

```bash
uv add passlib python-jose[cryptography] \
  prometheus-fastapi-instrumentator \
  psycopg[binary] psycopg_pool
```

### Project Structure

```
finna-app/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py (JWT auth)
│   │   │   ├── main.py (FastAPI app)
│   │   │   ├── routes/
│   │   │   │   ├── costs.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── config.py
│   │   │   │   └── extractors.py
│   ├── frontend/
│   │   └── src/
│   │       ├── services/
│   │       │   └── apiClient.ts
│   │       ├── hooks/
│   │       │   └── useApi.ts
│   │       ├── components/
│   │       │   ├── common/
│   │       │   │   └── APIScreen.tsx
│   │       │   └── auth/
│   │       │       └── LoginScreen.tsx
│   │       └── data/
│   │           └── mock_api_data.json
```

## Testing

### Backend Verification

```bash
cd /root/projects/finna-app
python3 -m py_compile backend/app/api/routes/costs.py
python3 -m py_compile backend/app/api/routes/alerts.py
python3 -m py_compile backend/app/api/auth.py
```

### Start Services

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Start backend
uv run uvicorn backend.app.api.main:app --reload

# Start frontend
cd backend/frontend && npm run dev
```

### Test Endpoints

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/api/v1/costs
curl http://localhost:8000/api/v1/alerts
```

## Deployment

### Automated Startup

```bash
./startup.sh
```

### Verification

```bash
./verify_setup.sh
```

## Troubleshooting

### Common Issues

1. **Missing dependencies**
   ```bash
   uv add passlib python-jose[cryptography] \
     prometheus-fastapi-instrumentator
   ```

2. **Import errors**
   - Ensure `__init__.py` exists in all packages
   - Check imports match directory structure

3. **Database connection**
   ```bash
   docker-compose up -d postgres
   sleep 10
   ```

### Budget Optimization Tips

- Use task prioritization for agent assignments
- Enable parallel processing where possible
- Cache results to avoid redundant work
- Reuse existing patterns from similar projects
- Focus on high-impact features first

## Files Created/Modified

### Backend
- `backend/app/api/routes/costs.py`
- `backend/app/api/routes/alerts.py`
- `backend/app/api/auth.py`
- `backend/app/api/main.py`
- `backend/app/api/routes/__init__.py`
- `backend/utils/__init__.py`
- `backend/utils/encryption.py`

### Frontend
- `backend/frontend/src/services/apiClient.ts`
- `backend/frontend/src/hooks/useApi.ts`
- `backend/frontend/src/components/common/APIScreen.tsx`
- `backend/frontend/src/components/auth/LoginScreen.tsx`
- `backend/frontend/src/data/mock_api_data.json`

### Scripts
- `startup.sh`
- `verify_setup.sh`
- `agent_orchestration.sh`

### Documentation
- `README_INTEGRATION.md`
- `INTEGRATION.md`
- `BACKEND_INTEGRATION.md`
- `MVP_COMPLETE.md`
- `FINAL_STATUS.md`
- `COMPLETION_REPORT.md`

## Access Information

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Username**: admin
- **Password**: admin

## Budget Optimization

Optimized for 75% efficiency (150k/200k tokens):
- Backend: 60,000 tokens (30%)
- Frontend: 70,000 tokens (35%)
- Architect: 30,000 tokens (15%)
- Testing: 20,000 tokens (10%)
- Docs: 20,000 tokens (10%)
- Savings: 50,000 tokens 💰
