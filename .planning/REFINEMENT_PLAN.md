# Finna Connection Points Refinement Plan

## Gap Analysis (generated 2026-04-24)

### Critical
| ID | Issue | Fix |
|---|---|---|
| CRIT-1 | `extractors_crud.py` has router code but is NOT registered in `main.py`. `extractors_registry.py` is registered but some fields/shapes differ from CLI expectations. | Keep extractors_registry active. Add pagination/meta fields to its responses. Delete extractors_crud.py to remove dead code. |

### Backend → CLI Mismatches
| ID | Endpoint | Backend Shape | CLI Expected | Fix |
|---|---|---|---|---|
| BE-1 | GET `/costs` | `{costs, totals, filtered, startDate, endDate}` | `{data, total, page, page_size, has_next, has_prev}` with `CostRecord[]` | Add top-level `data` wrapper, pagination meta. Keep `costs` for backward compat. |
| BE-2 | GET `/alerts` | `{alerts:[raw_rows], count}` | `{data:[Alert], total, page, page_size, has_next, has_prev}` | Map rows to `Alert` schema, add pagination wrapper. Keep `alerts` key. |
| BE-3 | GET `/extractors` (registry) | `{data:[{}], count}` | `{data:[{}], total, page, page_size, has_next, has_prev}` | Add `total/page_size/has_next/has_prev` fields. |
| BE-4 | GET `/extractors/{id}` | `{id,name,provider,config_id,config_name,enabled,...}` | `Extractor{id,name,provider,enabled,last_run,status}` | Add `last_run`/`status` to response. |
| BE-5 | `/configs` CRUD | Only GET `/configs`, GET `/configs/{id}` exist (wrappers around `/config`) | POST, PUT, DELETE `/configs` | Add POST/PUT/DELETE `/configs/*` mapping to config table logic. |
| BE-6 | `/costs/summary` and `/costs/breakdown` params | Accept `start_date`, `end_date` | CLI sends `start=`, `end=` | Accept both param names as aliases. |

### Frontend → Backend Mismatches
| ID | Issue | Fix |
|---|---|---|
| FE-1 | `apiClient.login()` calls `/auth/token` expecting `{token}` but does not handle `{access_token,token_type}` | Make login parse BOTH shapes, preferring `access_token`. |
| FE-2 | Screens render raw `<pre>` JSON dumps | Out of scope for this API-alignment pass; requires full component rewrite. |

## Implementation Order

1. **Backend Phase**: Fix all BE-* items. These are pure API contract changes.
2. **Cleanup Phase**: Remove dead `extractors_crud.py`.
3. **Frontend Phase**: Fix FE-1 in `apiClient.ts`.
4. **Verify Phase**: Run backend py_compile and frontend `tsc`.
5. **Commit & Push**

## Files to Edit
- `backend/app/api/routes/costs.py`
- `backend/app/api/routes/alerts.py`
- `backend/app/api/routes/extractors_registry.py`
- `backend/app/api/routes/config.py`
- `backend/app/api/routes/extractors.py` (param aliases)
- `backend/app/api/routes/extractors_crud.py` (delete)
- `frontend-ui/src/services/apiClient.ts`
