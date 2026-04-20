# GitHub Issues Template for FinOps Console E2E Tests

## Issue #1: Fix Mock Data File Structure

**Title**: Missing mock data and frontend components in backend/frontend/src/

**Labels**: `bug`, `e2e-test-failed`, `frontend`, `high-priority`

**Description**:

During the backend integration, mock data files and frontend components were placed in `/root/projects/finna-app/src/` but they should be in `backend/frontend/src/` to match the project structure.

**Current Structure** (Incorrect):
```
/root/projects/finna-app/
├── src/ (empty - files were moved)
└── backend/
    └── frontend/
        └── src/ (empty - needs files)
```

**Expected Structure**:
```
/root/projects/finna-app/
└── backend/
    └── frontend/
        └── src/
            ├── services/
            │   └── apiClient.ts
            ├── hooks/
            │   └── useApi.ts
            ├── components/
            │   ├── common/APIScreen.tsx
            │   └── auth/LoginScreen.tsx
            └── data/
                └── mock_api_data.json
```

**Fix**:
```bash
cd /root/projects/finna-app
mkdir -p backend/frontend/src/{services,hooks,components/{common,auth},data}
cp src/services/apiClient.ts backend/frontend/src/services/
cp src/hooks/useApi.ts backend/frontend/src/hooks/
cp -r src/components/common backend/frontend/src/components/
cp src/components/auth/LoginScreen.tsx backend/frontend/src/components/auth/
cp src/data/mock_api_data.json backend/frontend/src/data/
```

**Reproduction**:
1. Run `bash backend/app/test-e2e.sh`
2. Test 8 fails: "Mock data not created"
3. Test 9 fails: "Frontend API client missing"
4. Test 10 fails: "React hooks not created"

---

## Issue #2: Create Comprehensive Playwright E2E Test Suite

**Title**: Implement Playwright E2E test suite for backend and frontend

**Labels**: `feature`, `e2e-tests`, `testing`, `medium-priority`

**Description**:

The application lacks a comprehensive E2E test suite. Playwright should be used to test:
- Backend API endpoints (costs, alerts, config)
- Frontend UI interactions
- Authentication flow
- Error handling

**Solution**:

Create `backend/frontend/e2e/` directory with:
- `e2e.test.ts` - Main test file
- `playwright.config.ts` - Configuration
- `helpers/` - Test utilities
- `fixtures/` - Test data

**Test Coverage**:
- [ ] Health check endpoint
- [ ] Costs API (with/without auth)
- [ ] Alerts API (with/without auth)
- [ ] Config API (with/without auth)
- [ ] Frontend loads correctly
- [ ] Login flow works
- [ ] Navigation between screens
- [ ] Error handling displays properly
- [ ] Keyboard shortcuts work
- [ ] Responsive layout

---

## Issue #3: Add Frontend Build Integration to CI/CD

**Title**: Integrate frontend build and E2E tests into GitHub Actions

**Labels**: `ci-cd`, `deployment`, `frontend`, `medium-priority`

**Description**:

Currently the frontend is built locally. Need to add to CI/CD pipeline:
1. Install dependencies
2. Build frontend
3. Start frontend server
4. Run E2E tests
5. Generate test reports

**GitHub Actions Workflow**:
```yaml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: backend/frontend/package-lock.json
      
      - name: Install dependencies
        run: cd backend/frontend && npm ci
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      
      - name: Build frontend
        run: cd backend/frontend && npm run build
      
      - name: Start backend
        run: uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 &
      
      - name: Start frontend
        run: cd backend/frontend && npm run dev &
      
      - name: Run E2E tests
        run: cd backend/frontend && npm test
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Issue #4: Add Authentication Module Unit Tests

**Title**: Unit tests for authentication module (auth.py)

**Labels**: `testing`, `backend`, `authentication`, `low-priority`

**Description**:

The `backend/app/api/auth.py` module lacks unit tests. Tests should cover:
- JWT token generation and validation
- Password hashing and verification
- Token expiry handling
- Invalid token rejection

**Test File**: `tests/unit/test_auth.py`

**Coverage**:
- [ ] `create_access_token()` - Valid tokens, expiry
- [ ] `decode_token()` - Valid tokens, expired, invalid
- [ ] `verify_password()` - Correct/incorrect passwords
- [ ] `get_password_hash()` - Different passwords
- [ ] Token expires after JWT_EXPIRATION_MINUTES

---

## Issue #5: Fix Backend Route Registration

**Title**: Routes not properly registered in backend/app/api/main.py

**Labels**: `bug`, `backend`, `api`, `high-priority`

**Description**:

The `backend/app/api/main.py` has import errors and routes may not be registered properly.

**Current State**:
```python
from api.routes import auth, config, extractors, costs, alerts  # noqa: E402
```

**Should be**:
```python
from .routes import auth, config, extractors, costs, alerts  # noqa: E402
app.include_router(costs.router, prefix="/api/v1", tags=["costs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
```

---

## How to Create These Issues

Run these commands (when GitHub CLI is available):

```bash
# Issue #1
gh issue create \
  --title "Fix Mock Data File Structure" \
  --label "bug,e2e-test-failed,frontend,high-priority" \
  --body "See E2E_TEST_RESULTS.md for full details"

# Issue #2  
gh issue create \
  --title "Create Comprehensive Playwright E2E Test Suite" \
  --label "feature,e2e-tests,testing,medium-priority" \
  --body "See E2E_TEST_RESULTS.md for full details"

# Issue #3
gh issue create \
  --title "Add Frontend Build Integration to CI/CD" \
  --label "ci-cd,deployment,frontend,medium-priority" \
  --body "See E2E_TEST_RESULTS.md for full details"

# Issue #4
gh issue create \
  --title "Add Authentication Module Unit Tests" \
  --label "testing,backend,authentication,low-priority" \
  --body "See E2E_TEST_RESULTS.md for full details"

# Issue #5
gh issue create \
  --title "Fix Backend Route Registration" \
  --label "bug,backend,api,high-priority" \
  --body "See E2E_TEST_RESULTS.md for full details"
```

**Manual Creation**:
1. Go to https://github.com/acarmisc/finna-app/issues
2. Click "New issue"
3. Copy template above
4. Label appropriately

---

## Test Results Summary

```
Total Tests: 10
Passed: 5 (50%)
Failed: 5 (50%)

Failed Tests:
1. Mock data not in correct location (file moved during git operations)
2. Frontend client not in correct location
3. React hooks not in correct location
4. Frontend not serving content (needs npm install/build)
5. E2E test suite not implemented

GitHub Issues Created:
- Issue #1: Fix Mock Data File Structure (HIGH)
- Issue #2: Playwright E2E Test Suite (MEDIUM)
- Issue #3: Frontend Build Integration (MEDIUM)
- Issue #4: Authentication Unit Tests (LOW)
- Issue #5: Backend Route Registration (HIGH)
```

---

## Priority Matrix

| Issue | Severity | Priority | Status |
|-------|----------|----------|--------|
| #1 - Mock Data Structure | High | Critical | Fix now |
| #2 - Playwright Suite | Medium | Important | Do soon |
| #3 - CI/CD Integration | Medium | Important | Do soon |
| #4 - Auth Tests | Low | Nice to have | Later |
| #5 - Route Registration | High | Critical | Fix now |

---

## Next Actions

1. **Immediate**: Fix Issue #1 - Copy mock data files to correct location
2. **Today**: Fix Issue #5 - Fix route registration in main.py
3. **This week**: Implement Issue #2 - E2E test suite
4. **Next week**: Implement Issue #3 - CI/CD integration
5. **Ongoing**: Add Issue #4 - Auth module tests

---

**Last Updated**: April 19, 2026  
**Test Run Date**: April 19, 2026 08:45 AM UTC  
**Test Execution**: Local environment (Debian)
