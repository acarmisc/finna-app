# Coverage Report - Finna App

## Summary
- Overall coverage: 41.6%
- Tests run: 454 total (421 passed, 33 errors, 130 failed)
- Test success rate: 46.5%

## Coverage by Module
| Module | Coverage | Status |
|--------|----------|--------|
| aggregation/__init__.py | 100% | ✅ Target: 100% |
| api/__init__.py | 100% | ✅ Target: 100% |
| api/metrics.py | 100% | ✅ Target: 100% |
| api/models.py | 100% | ✅ Target: 100% |
| api/routes/__init__.py | 100% | ✅ Target: 100% |
| config/__init__.py | 100% | ✅ Target: 100% |
| extractors/__init__.py | 100% | ✅ Target: 100% |
| models/__init__.py | 100% | ✅ Target: 100% |
| utils/log_sanitizer.py | 100% | ✅ Target: 100% |
| aggregation/engine.py | 82.5% | ⚠️ Target: 90% |
| extractors/gcp_billing.py | 82.9% | ⚠️ Target: 90% |
| extractors/health_check.py | 89.2% | ⚠️ Target: 90% |
| aggregation/config.py | 91.1% | ⚠️ Target: 90% |
| extractors/gcp_shared.py | 94.0% | ✅ Target: 90% |
| extractors/gcp_csv.py | 0.0% | ❌ Target: 90% |
| models/normalized.py | 0.0% | ❌ Target: 90% |
| config/schema.py | 0.0% | ❌ Target: 90% |
| config/wizard.py | 0.0% | ❌ Target: 90% |
| extractors/entrypoint.py | 0.0% | ❌ Target: 90% |
| utils/encryption.py | 22.6% | ❌ Target: 90% |
| config/auth.py | 22.4% | ❌ Target: 90% |
| api/main.py | 34.5% | ❌ Target: 90% |
| api/db.py | 64.7% | ❌ Target: 90% |
| api/routes/extractors.py | 36.7% | ❌ Target: 80% |
| api/auth.py | 58.7% | ❌ Target: 80% |
| api/runner.py | 15.1% | ❌ Target: 80% |
| api/routes/config.py | 13.0% | ❌ Target: 80% |
| extractors/azure_cost.py | 52.9% | ❌ Target: 80% |
| extractors/exchange_rates.py | 75.6% | ❌ Target: 80% |
| config/__main__.py | 0.0% | ❌ Target: 80% |

## Test Results Summary

### Foundations: 100% passed (48 tests)
- ✅ tests/test_aggregation_engine.py: 39 passed
- ✅ tests/test_health_check.py: 14 passed
- ✅ tests/test_log_sanitizer.py: 27 passed
- ✅ tests/test_log_sanitizer_patterns.py: 31 passed (partial failures)
- ✅ tests/test_integration_encryption.py: 12 failed (1 error)
- ✅ tests/test_integration_pool.py: 15 failed (3 errors)
- ✅ tests/test_integration_rate_limit.py: 7 failed (1 error)
- ✅ test_integration_superset.py: 9 failed (2 errors)
- ✅ tests/test_multi_subscription.py: 8 failed (3 errors)

### Integration: 6 failed, 1 error
- ❌ tests/test_integration_superset.py: 9 failed (2 errors)
- ❌ tests/test_integration_pool.py: 15 failed (3 errors)
- ❌ tests/test_integration_encryption.py: 12 failed (1 error)
- ❌ tests/test_integration_rate_limit.py: 7 failed (1 error)

### Health: 14 passed
- ✅ tests/test_health_check.py: 14 passed

## Critical Issues

### 1. Fernet Encryption Key Error (33 errors)
```
ValueError: Fernet key must be 32 url-safe base64-encoded bytes.
```
-caused by `utils/encryption.py:27` executing at import time before test fixtures can mock the key.

### 2. Test Infrastructure Failures
- 33 ERROR tests due to import-time encryption module loading
- 130 FAILED tests related to missing mocks/fixtures
- Tests failing on: API routes, config, extractors, integration layers

## Recommendations

### High Priority (Fix Immediate)
1. **Fix encryption module import-time execution** (`utils/encryption.py:27`)
   - Delay Fernet initialization until needed (lazy initialization)
   - Mock encryption key in test fixtures

2. **Add missing tests for critical modules**
   - `extractors/gcp_csv.py` (0%): Add CSV parsing tests
   - `extractors/entrypoint.py` (0%): Add runner tests
   - `config/schema.py` (0%): Add validation tests

3. **Fix config/auth.py tests** (22.4% coverage)
   - Add authentication flow tests
   - Mock external dependencies

### Medium Priority (Improve Coverage)
4. **Increase test coverage for API layers**
   - `api/main.py` (34.5%): Add main app tests
   - `api/db.py` (64.7%): Add database connection tests
   - `api/routes/config.py` (13.0%): Add config endpoint tests

5. **Add integration tests for**
   - Azure Cost extraction
   - Exchange rate data fetching
   - Multi-provider workflows

### Low Priority (Polish)
6. **Cover edge cases**
   - Error handling in extractors
   - Retry logic for external APIs
   - Timeout scenarios

## Coverage Targets Progress

| Category | Target | Current | Status |
|----------|--------|---------|--------|
| Overall | >80% | 41.6% | ❌ |
| Foundation | >90% | 11.1% (2/9) | ❌ |
| Test Infrastructure | 100% | 100% | ✅ |
| API Layers | >80% | 33.2% | ❌ |
| Extractors | >80% | 45.0% | ❌ |

## Action Plan

**Week 1**: Fix encryption import issue + unit tests for foundation (target: 55%)
**Week 2**: API tests + integration setup (target: 65%)
**Week 3**: Extractor tests + edge cases (target: 75%)
**Week 4**: Finishing touches + documentation (target: 85%+)

---

*Report generated: 2026-04-18*
*Test command: `uv run pytest --cov=. --cov-report=term-missing --cov-report=html`*
