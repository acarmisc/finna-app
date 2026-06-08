# FinOps Console - Integration Guide

## Overview

This document describes how to deploy and run the FinOps Console backend API.

## Architecture

```
┌─────────────────┐
│   Backend API   │  FastAPI/Python
│   (FastAPI)     │  - Costs
├─────────────────┤  - Alerts
│   PostgreSQL    │  - Extractors
└─────────────────┘  - Data storage
```

## Quick Start

### 1. Prerequisites

- Docker and docker-compose
- Python 3.11+
- uv (Python package manager)

### 2. Start Backend Services

```bash
# Navigate to project directory
cd /path/to/finna-app

# Start Docker services
docker-compose up -d postgres

# Start the FastAPI backend
uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the Application

- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## API Endpoints

### Authentication

- `POST /api/v1/auth/token` - Get authentication token
- `POST /api/v1/auth/logout` - Logout

### Config/Connections

- `GET /api/v1/config` - List all configurations
- `POST /api/v1/config` - Create new configuration
- `GET /api/v1/config/{id}` - Get configuration by ID
- `PUT /api/v1/config/{id}` - Update configuration
- `DELETE /api/v1/config/{id}` - Delete configuration

### Costs

- `GET /api/v1/costs` - Get cost records with filtering
- `GET /api/v1/costs/totals` - Get aggregated cost totals
- `GET /api/v1/costs/by-sku` - Get costs grouped by SKU
- `GET /api/v1/costs/daily` - Get daily cost breakdown

### Alerts

- `GET /api/v1/alerts` - Get alerts with filtering
- `GET /api/v1/alerts/stats` - Get alert statistics
- `GET /api/v1/alerts/active` - Get active firing alerts
- `GET /api/v1/alerts/health` - Get extractor health status

### Extractors/Runs

- `GET /api/v1/extractors/status` - Get recent extractor runs
- `POST /api/v1/extractors/run` - Start an extractor
- `GET /api/v1/extractors/status/{run_id}` - Get run details
- `POST /api/v1/extractors/cancel/{run_id}` - Cancel a run

### Projects

- `GET /api/v1/config/projects` - List all projects
- `POST /api/v1/config/projects` - Create new project

### Health

- `GET /healthz` - Backend health check

## Authentication

### JWT Tokens

- Tokens are JWT format
- Included in Authorization header as `Bearer <token>`
- Tokens expire after configurable duration (configurable via `JWT_EXPIRATION_MINUTES`)

### Login Flow

1. Client sends credentials to `POST /api/v1/auth/token`
2. Backend validates and returns token
3. All subsequent requests include `Authorization: Bearer <token>`
4. On logout, call `POST /api/v1/auth/logout`

## Development

### Running Tests

```bash
# Backend tests
uv run pytest
```

### Environment Variables

```bash
export DATABASE_URL=postgresql://finops:change-me-set-real-password@localhost:5432/finops
export JWT_SECRET=change-me-set-real-secret-at-least-32-chars
export ALLOWED_ORIGINS=http://localhost:3000
```

## Troubleshooting

### Backend Not Starting

1. Check PostgreSQL is running: `docker-compose ps`
2. Check logs: `docker-compose logs postgres api`
3. Verify database is initialized

### Authentication Issues

1. Check token expiry
2. Verify JWT_SECRET matches between auth and validation
3. Check database for user credentials

## Architecture Diagram

```mermaid
graph TD
    A[API Client] --> B[FastAPI Backend]
    B --> C[PostgreSQL]
    B --> D[Extractors]
    D --> C
```

## Next Steps

1. Configure authentication with your identity provider
2. Set up cost data sources (GCP, Azure, LLM)
3. Configure alerting rules
4. Deploy to production environment

## Support

For issues or questions:
- Check API documentation: http://localhost:8000/docs
- Review logs: `docker-compose logs`
- Check GitHub issues
