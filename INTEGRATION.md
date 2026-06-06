# FinOps Console - Integration Guide

## Overview

This document describes how to deploy and run the FinOps Console with backend-to-frontend integration.

## Architecture

```
┌─────────────────┐
│   Frontend      │  React/TypeScript
│   (SPA)         │  - Dashboard
├─────────────────┤  - Cost Explorer
│   Backend API   │  - Alerts
│   (FastAPI)     │  - Projects
├─────────────────┤
│   PostgreSQL    │  - Data storage
└─────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker and docker-compose
- Python 3.11+
- uv (Python package manager)

### 2. Start Backend Services

```bash
# Navigate to project directory
cd /root/projects/finna-app

# Start Docker services
docker-compose up -d postgres

# Wait for PostgreSQL to initialize
sleep 10

# Start the FastAPI backend
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend

```bash
# In a separate terminal
cd /root/projects/finna-app/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:5173
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

## Frontend Integration

### Authentication Flow

1. User enters credentials on login screen
2. Frontend calls `POST /api/v1/auth/token`
3. Token is stored in localStorage
4. All subsequent requests include Authorization header
5. On logout, token is cleared

### Data Loading

```typescript
// Example: Load costs with filtering
import { getApiClient } from '../services/apiClient';

const client = getApiClient();
const response = await client.getCosts({
  provider: 'gcp',
  startDate: '2025-11-01',
  endDate: '2025-11-15'
});

if (response.error) {
  console.error(response.error.message);
} else {
  // Use response.data
  console.log(response.data);
}
```

### Using React Hooks

```typescript
// Example: Use the useCosts hook in a component
import { useCosts } from '../hooks/useApi';

function CostExplorer() {
  const { data: costs, loading, error, refresh } = useCosts({
    provider: 'gcp'
  });

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen error={error} />;
  
  return (
    <div className="cost-explorer">
      <h2>Cost Explorer</h2>
      <button onClick={refresh}>Refresh</button>
      {/* Render costs */}
    </div>
  );
}
```

## Error Handling

### Network Errors

```typescript
const response = await client.getCosts();

if (response.error) {
  switch (response.error.error) {
    case 'network_error':
      console.log('Network error - check connection');
      break;
    case 'api_error':
      console.log(`API error: ${response.error.message}`);
      break;
    case 'parse_error':
      console.log('Failed to parse response');
      break;
  }
}
```

### UI Error States

The frontend includes error handling:
- **APIScreen**: Shows error banner when backend is inaccessible
- **ErrorBoundary**: Catches React errors and shows reload button
- **LoadingScreen**: Shows spinner during data loading
- **Toast notifications**: Displays success/error messages

## Authentication

### JWT Tokens

- Tokens are JWT format
- Stored in localStorage
- Included in Authorization header as `Bearer <token>`
- Tokens expire after configurable duration (configurable in FastAPI)

### Login Flow

1. User visits login page
2. Enters username and password
3. Frontend sends credentials to backend
4. Backend validates and returns token
5. Frontend stores token and redirects to dashboard

### Token Refresh

```typescript
// Check if token is expired
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch (e) {
    return true;
  }
}

// Auto-refresh token
async function refreshToken(): Promise<boolean> {
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('finna-auth-token', data.token);
    return true;
  }
  
  return false;
}
```

## Development

### Running Tests

```bash
# Backend tests
uv run pytest

# Frontend tests (in frontend directory)
npm test
```

### Environment Variables

```bash
# Backend
export VITE_API_URL=http://localhost:8000
export DATABASE_URL=postgresql://finops:change-me-set-real-password@localhost:5432/finops
export JWT_SECRET=change-me-set-real-secret-at-least-32-chars

# Frontend
export API_URL=http://localhost:8000
```

## Troubleshooting

### Backend Not Starting

1. Check PostgreSQL is running: `docker-compose ps`
2. Check logs: `docker-compose logs postgres api`
3. Verify database is initialized

### Frontend Cannot Connect

1. Check CORS settings in backend
2. Verify API_URL environment variable
3. Check browser console for errors
4. Ensure backend is running on correct port

### Authentication Issues

1. Check token expiry
2. Verify JWT_SECRET matches between auth and validation
3. Check database for user credentials

## Architecture Diagram

```mermaid
graph TD
    A[Browser] --> B[Frontend React]
    B --> C[API Client]
    C --> D[FastAPI Backend]
    D --> E[PostgreSQL]
    D --> F[Extractors]
    F --> E
```

## Next Steps

1. Configure authentication with your identity provider
2. Set up cost data sources (GCP, Azure, LLM)
3. Configure alerting rules
4. Customize dashboard widgets
5. Deploy to production environment

## Support

For issues or questions:
- Check API documentation: http://localhost:8000/docs
- Review logs: `docker-compose logs`
- Check GitHub issues
