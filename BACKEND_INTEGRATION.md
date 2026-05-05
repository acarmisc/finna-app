# FinOps Console - Backend Integration

## Overview

This directory contains the backend integration for the FinOps Console frontend. It includes:

1. **FastAPI Backend** - RESTful API for all data operations
2. **Frontend Client** - TypeScript API client for seamless integration
3. **React Hooks** - Custom hooks for easy data management
4. **Authentication** - JWT-based authentication system
5. **Error Handling** - Comprehensive error states and recoveries

## Files Structure

```
finna-app/
├── api/                    # FastAPI backend
│   ├── routes/            # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py        # Authentication
│   │   ├── config.py      # Configuration management
│   │   ├── costs.py       # Cost data endpoints
│   │   ├── alerts.py      # Alert management
│   │   └── extractors.py  # Extractor orchestration
│   ├── main.py            # FastAPI app entrypoint
│   └── models.py          # Pydantic schemas
├── src/
│   ├── services/          # Frontend services
│   │   ├── apiClient.ts   # API client implementation
│   │   └── api.ts         # Legacy API client
│   ├── hooks/             # React hooks
│   │   ├── useApi.ts      # Data fetching hooks
│   │   └── useLocalStorage.ts
│   └── components/        # React components
│       └── common/        # Shared components
│           ├── APIScreen.tsx  # API-enabled screen wrapper
│           ├── LoadingScreen.tsx
│           └── ...
└── startup.sh             # Startup script
```

## Key Features

### 1. Backend API

The FastAPI backend provides:

- **RESTful Endpoints** - Clean, documented API
- **JWT Authentication** - Secure token-based auth
- **CORS Support** - Enabled for frontend development
- **Rate Limiting** - Protection against abuse
- **Automatic Documentation** - Swagger UI at `/docs`

### 2. Frontend Client

The TypeScript client provides:

- **Type Safety** - Full TypeScript support
- **Error Handling** - Comprehensive error states
- **Token Management** - Automatic token storage and refresh
- **Retry Logic** - Network error recovery

### 3. React Hooks

Custom hooks for easy data management:

- `useData()` - Generic data fetching
- `useList()` - Paginated lists
- `useCosts()` - Cost data with filtering
- `useAlerts()` - Alerts management
- `useRuns()` - Extractor runs
- `useConnections()` - Configuration management
- `useDashboardSummary()` - Dashboard data aggregation

### 4. Components

Reusable components:

- **APIScreen** - Screen wrapper with health check
- **LoadingScreen** - Loading state indicator
- **ErrorBoundary** - Error handling wrapper
- **Toast System** - Notification system

## Quick Start

### Method 1: Using Docker Compose

```bash
# Start services
docker-compose up -d postgres api

# Check backend health
curl http://localhost:8000/healthz

# Start frontend
cd frontend
npm install
npm run dev
```

### Method 2: Manual Setup

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Start backend
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (in another terminal)
cd frontend
npm run dev
```

## API Endpoints Reference

### Authentication

```typescript
// Login
await apiClient.login(username, password);

// Logout
await apiClient.logout();

// Check health
await apiClient.healthCheck();
```

### Costs

```typescript
// Get costs with filters
const costs = await apiClient.getCosts({
  provider: 'gcp',
  startDate: '2025-11-01',
  endDate: '2025-11-15'
});

// Get daily costs for chart
const daily = await apiClient.getDailyCosts({
  startDate: '2025-11-01',
  endDate: '2025-11-15',
  provider: 'gcp'
});

// Get costs by SKU
const bySku = await apiClient.getCostsBySku(50);
```

### Alerts

```typescript
// Get all alerts
const alerts = await apiClient.getAlerts({
  status: 'firing',
  severity: 'err',
  limit: 50
});

// Get active alerts
const active = await apiClient.getActiveAlerts();
```

### Extractors

```typescript
// Get runs
const runs = await apiClient.getRuns(50);

// Run an extractor
await apiClient.runExtractor('gcp_billing', 'gcp');
```

### Configurations

```typescript
// Get connections
const connections = await apiClient.getConnections();

// Create connection
await apiClient.createConnection({
  provider: 'gcp',
  name: 'Production GCP',
  config: { /* config data */ }
});
```

## React Hooks Usage

```typescript
import { useCosts, useAlerts, useRuns } from '../hooks/useApi';

function Dashboard() {
  const { 
    data: costs, 
    loading, 
    error, 
    refresh 
  } = useCosts({ provider: 'gcp' });
  
  const { data: alerts } = useAlerts();
  const { data: runs } = useRuns(10);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen error={error} />;

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      
      <section className="costs">
        <h2>Costs</h2>
        <CostList costs={costs} />
        <button onClick={refresh}>Refresh</button>
      </section>

      <section className="alerts">
        <h2>Alerts</h2>
        <AlertList alerts={alerts.alerts} />
      </section>

      <section className="runs">
        <h2>Recent Runs</h2>
        <RunList runs={runs} />
      </section>
    </div>
  );
}
```

## Error Handling

### Backend Errors

All API calls return `{ data, error, status }`:

```typescript
const response = await apiClient.getCosts();

if (response.error) {
  console.log('Error:', response.error);
  console.log('Status:', response.status);
  
  // Handle different error types
  switch (response.error.error) {
    case 'network_error':
      // Show network error UI
      break;
    case 'api_error':
      // Show API error UI
      break;
    case 'parse_error':
      // Show parse error UI
      break;
  }
} else {
  // Success - use response.data
  console.log(response.data);
}
```

### Frontend Error States

```typescript
// APIScreen component shows error banner
function MyScreen() {
  return (
    <APIScreen title="My Screen">
      {/* Content */}
    </APIScreen>
  );
}

// ErrorBoundary catches React errors
function App() {
  return (
    <ErrorBoundary>
      <Routes />
    </ErrorBoundary>
  );
}
```

## Authentication Flow

### 1. Login

```typescript
// User submits login form
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  
  const response = await apiClient.login(username, password);
  
  if (response.error) {
    setError(response.error.message);
  } else {
    // Navigate to dashboard
    navigate('/dashboard');
  }
};
```

### 2. Protected Routes

```typescript
// Check authentication before rendering
function ProtectedRoute({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  
  useEffect(() => {
    apiClient.healthCheck()
      .then(health => setAuthenticated(health.data?.status === 'ok'))
      .catch(() => setAuthenticated(false));
  }, []);
  
  if (!authenticated) {
    return <Navigate to="/login" />;
  }
  
  return children;
}
```

### 3. Logout

```typescript
const handleLogout = async () => {
  await apiClient.logout();
  navigate('/login');
};
```

## Testing

### Backend Tests

```bash
uv run pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Test

```bash
# Start backend
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &

# Start frontend
cd frontend && npm run dev &

# Test health check
curl http://localhost:8000/healthz

# Test login
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Test costs endpoint
curl http://localhost:8000/api/v1/costs \
  -H "Authorization: Bearer <token>"
```

## Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check PostgreSQL is running: `docker-compose ps`
   - Check logs: `docker-compose logs api`
   - Verify database URL in environment

2. **Frontend cannot connect**
   - Check CORS settings
   - Verify API_URL environment variable
   - Check browser console for errors

3. **Authentication failing**
   - Check token expiry
   - Verify JWT_SECRET matches
   - Check database credentials

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Enable CORS for development
export ALLOWED_ORIGINS="*"
```

## Next Steps

1. **Configure Real Data Sources**
   - Set up GCP billing exports
   - Configure Azure Cost Management
   - Add LLM gateway connections

2. **Customize Dashboards**
   - Add custom widgets
   - Configure alerts
   - Create templates

3. **Deploy to Production**
   - Set up production database
   - Configure authentication
   - Deploy frontend

## Support

- **API Documentation**: http://localhost:8000/docs
- **GitHub Issues**: Report bugs and request features
- **Documentation**: See INTEGRATION.md for detailed guides
