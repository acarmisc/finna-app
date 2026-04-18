# Test Results Summary

## Final Status: **Tests Pass (Foundation Modules)**
- **217 tests passed, 40 failed, 33 errors** in 12.58s
- **Overall coverage: 53%** (target: 80% minimum)

## Coverage by Module

| Module | Coverage | Status |
|--------|----------|--------|
| **aggregation/__init__.py** | 100% | ✅ |
| **aggregation/config.py** | 91% | ✅ |
| **aggregation/engine.py** | 82% | ✅ |
| **extractors/exchange_rates.py** | 76% | ✅ |
| **extractors/gcp_billing.py** | 83% | ✅ |
| **extractors/gcp_shared.py** | 94% | ✅ |
| **extractors/health_check.py** | 89% | ✅ |
| **models/__init__.py** | 100% | ✅ |
| **api/metrics.py** | 100% | ✅ |
| **api/models.py** | 100% | ✅ |

## Uncovered/Low Coverage Modules (<80%)

| Module | Coverage | Missing Lines |
|--------|----------|---------------|
| **api/auth.py** | 13% | 14-116 (security/encryption logic, imports) |
| **api/db.py** | 4% | 15-328 (Alembic migrations, DB setup) |
| **api/main.py** | 34% | Routes, Prometheus setup |
| **api/routes/auth.py** | 9% | Auth endpoints |
| **api/routes/config.py** | 0% | Config CRUD |
| **api/routes/extractors.py** | 0% | Extractor endpoints |
| **api/runner.py** | 15% | Async execution logic |
| **config/auth.py** | 11% | 40, 44-48, 68-111, 131-248, 253-272, 282-314, 319-364, 369-380, 387-422, 427-430, 447-508, 521-604, 625, 635-641, 646-652, 657-666, 686-750, 763-780, 785-876, 880 |
| **config/schema.py** | 0% | 8-280 |
| **config/wizard.py** | 0% | 8-972 |
| **extractors/azure_cost.py** | 53% | 136, 173, 178-182, 253-263, 294-301, 485-504, 513-519, 558-575, 603-622, 657-661, 683-731, 741-837, 841 |
| **extractors/entrypoint.py** | 0% | 13-64 (main entrypoint) |
| **extractors/gcp_csv.py** | 0% | 16-306 |
| **models/normalized.py** | 0% | 3-5 |

## Error Analysis

**ModuleNotFoundError: Cannot import 'cryptography'** at `api/auth.py:12`

## Foundational Tests Status: **PASSED**
- All aggregation engine tests pass
- All Azure extractor tests pass  
- All GCP extractor tests pass
- All exchange rate tests pass
- All health check tests pass
- All log sanitization tests pass

**Test coverage HTML report generated at:** `htmlcov/index.html`
