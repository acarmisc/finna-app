# Implementazione: FastAPI Orchestrator + CLI → API

## Obiettivo

Aggiungere un'applicazione FastAPI che funge da orchestratore centralizzato per il
sistema FinOps. L'API riceve credenziali e configurazioni dalla CLI (o direttamente),
le persiste nel DB, ed esegue gli estrattori come subprocess.

La CLI (`config/auth.py`) diventa **dual-mode**:
- **Locale** (default): come oggi, salva in keyring
- **Remoto** (`--api-url`): dopo l'auth, pusha la configurazione all'API

## Architettura

```
┌────────────┐      POST /api/v1/config       ┌─────────────────┐
│  CLI auth  │ ──────────────────────────────→ │   FastAPI API    │
│ (locale)   │      POST /api/v1/extractors/run │   (orchestrator) │
└────────────┘                                  └────────┬────────┘
                                                         │
                                          ┌──────────────┼──────────────┐
                                          │ subprocess   │ subprocess   │ subprocess
                                          ▼              ▼              ▼
                                    azure_cost    gcp_billing   exchange_rates
                                          │              │              │
                                          └──────────────┼──────────────┘
                                                         ▼
                                                   PostgreSQL
                                              (cost_records, cloud_config,
                                               extractor_runs, extractor_health)
```

## Flusso operativo

### 1. Setup iniziale (dopo deploy del cluster)

```bash
# Autenticazione interattiva + push all'API
python -m config.auth azure --auto-select --api-url https://finna.example.com

# Oppure, registrazione diretta (service principal)
curl -X POST https://finna.example.com/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "credential_type": "service_principal",
    "config": {
      "tenant_id": "...",
      "client_id": "...",
      "client_secret": "...",
      "subscription_id": "...",
      "resource_groups": ["RG1", "RG2"],
      "scope": "resourcegroup"
    }
  }'
```

### 2. Esecuzione estrazione

```bash
# Via API
curl -X POST https://finna.example.com/api/v1/extractors/run \
  -d '{"provider": "azure"}'

# Via CLI
python -m config.auth azure --run --api-url https://finna.example.com
```

### 3. Monitoraggio

```bash
curl https://finna.example.com/api/v1/extractors/status
curl https://finna.example.com/api/v1/extractors/health
curl https://finna.example.com/api/v1/config
```

---

## Modifiche al DB

### Nuova tabella: `cloud_config`

```sql
CREATE TABLE cloud_config (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    provider        TEXT NOT NULL CHECK (provider IN ('azure', 'gcp')),
    name            TEXT NOT NULL,
    credential_type TEXT NOT NULL DEFAULT 'service_principal'
        CHECK (credential_type IN ('service_principal', 'managed_identity', 'cli', 'device_code')),
    config          JSONB NOT NULL,
    -- Azure: {tenant_id, client_id, client_secret, subscription_id, resource_groups, scope, ...}
    -- GCP:   {project_id, billing_account_id, bigquery_dataset, bigquery_table, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cloud_config_provider ON cloud_config (provider);
```

### Nuova tabella: `extractor_runs`

```sql
CREATE TABLE extractor_runs (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    config_id         TEXT NOT NULL REFERENCES cloud_config(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    extractor_type    TEXT NOT NULL,  -- 'azure_cost' | 'gcp_billing' | 'exchange_rates'
    status            TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    records_extracted INTEGER DEFAULT 0,
    error_message     TEXT,
    log_output        TEXT,
    pid              INTEGER
);

CREATE INDEX idx_extractor_runs_status ON extractor_runs (status);
CREATE INDEX idx_extractor_runs_config ON extractor_runs (config_id);
```

### Migrazione `sql/migrations/001_cloud_config.sql`

Contiene le due CREATE TABLE sopra. Da eseguire dopo `init.sql`.

---

## Nuovi file

### `api/__init__.py`
Vuoto.

### `api/main.py` (~120 righe)
- FastAPI app con lifecycle (connection pool PG)
- Mount router: `/api/v1/config`, `/api/v1/extractors`, `/api/v1/auth`
- Health endpoint `GET /healthz`
- CORS middleware (per CLI da locale)
- Legge `PG_DSN` da env

### `api/db.py` (~80 righe)
- Connection pool psycopg (singleton)
- `get_db()` dependency per FastAPI
- Helper per query su `cloud_config` e `extractor_runs`
- `init_db()`: crea tabelle se non esistono (idempotente)

### `api/runner.py` (~120 righe)
- `start_extractor(config_id, provider, extractor_type, pg_dsn)` → subprocess
  - Costruisce env vars dal `cloud_config.config` JSON
  - Lancia `python -m extractors.{type}` con env vars + PG_DSN
  - Registra run in `extractor_runs` (status='running')
  - Monitora processo (poll, cattura output)
  - Aggiorna `extractor_runs` a fine (status='success'/'failed')
- `list_runs(pg_dsn, limit)` → lista run recenti
- `get_run(run_id, pg_dsn)` → dettaglio singolo run
- Gestione timeout (default 30 min)

### `api/routes/config.py` (~200 righe)
- `GET    /api/v1/config`             → lista tutte le configurazioni
- `POST   /api/v1/config`             → crea configurazione (valida provider + campi)
- `GET    /api/v1/config/{id}`        → dettaglio configurazione
- `PUT    /api/v1/config/{id}`        → aggiorna configurazione
- `DELETE /api/v1/config/{id}`        → elimina configurazione
- Schema Pydantic per request/response per provider

### `api/routes/extractors.py` (~180 righe)
- `POST /api/v1/extractors/run`       → avvia estrazione
  - Body: `{provider, config_id?, extractor_type?}`
  - Se `config_id` omesso, usa prima config per quel provider
  - Chiama `runner.start_extractor()`
  - Response: `{run_id, status, config_id}`
- `GET  /api/v1/extractors/status`    → lista run recenti (ultimi 50)
- `GET  /api/v1/extractors/status/{id}` → dettaglio singolo run
- `GET  /api/v1/extractors/health`    → health per extractor (lega a health_check.py)
- `POST /api/v1/extractors/cancel/{id}` → kill subprocess (graceful + force dopo 10s)

### `api/routes/auth.py` (~150 righe)
- `POST /api/v1/auth/azure/device-code` → avvia device code flow server-side
  - Ritorna `{verification_uri, user_code, device_code, expires_in, interval}`
  - Salva `device_code` + `tenant_id` in memoria per polling
- `POST /api/v1/auth/azure/device-code/poll` → polla per token completato
  - Body: `{device_code, tenant_id}`
  - Se completato: salva `cloud_config` nel DB, ritorna `{config_id}`
- `POST /api/v1/auth/gcp/register` → registra ADC/keyfile
  - Body: `{project_id, key_file_content?}`
  - Salva in `cloud_config`
- Nota: device code server-side richiede `azure-identity` lato API

### `api/models.py` (~100 righe)
- Pydantic schemas per request/response:
  - `CloudConfigCreate`, `CloudConfigResponse`, `CloudConfigUpdate`
  - `ExtractorRunRequest`, `ExtractorRunResponse`, `ExtractorStatusResponse`
  - `DeviceCodeStart`, `DeviceCodePoll`, `DeviceCodeResult`
- Separazione dai modelli DB (nessun accoppiamento)

---

## Modifiche a file esistenti

### `config/auth.py` (~50 righe nuove)
- Aggiungere parametro `--api-url` a `argparse`
- Aggiungere funzione `push_config_to_api(meta, api_url)`:
  - `POST {api_url}/api/v1/config` con il meta dict dell'auth
  - Se `api_url` fornito, dopo auth chiama push automaticamente
- Modificare `azure_auth_interactive()`: se `api_url` presente, dopo il keyring salva,
  chiama `push_config_to_api()`
- Aggiungere funzione `run_extractor_via_api(provider, api_url)`:
  - `POST {api_url}/api/v1/extractors/run`

### `extractors/azure_cost.py` (~20 righe modificate)
- `main()`: aggiungere fallback lettura `cloud_config` da DB oltre a env vars + keyring
- `discover_azure_subscriptions_from_db(pg_dsn)`: legge da `cloud_config` dove `provider='azure'`
- Priority: env vars → keyring → DB `cloud_config`

### `extractors/gcp_billing.py` (~15 righe modificate)
- `main()`: aggiungere fallback lettura da `cloud_config` per GCP
- `discover_gcp_configs_from_db(pg_dsn)`: legge da `cloud_config` dove `provider='gcp'`

### `pyproject.toml` (~3 righe nuove)
- Aggiungere dipendenze: `fastapi>=0.115`, `uvicorn[standard]>=0.30`

### `Dockerfile.api` (nuovo, ~45 righe)
- Multi-stage come `Dockerfile.extractor`
- Aggiungere copia di `api/`
- `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`

### `docker-compose.yml` (~20 righe nuove)
- Aggiungere servizio `api`:
  ```yaml
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports: ["8000:8000"]
    environment:
      PG_DSN: postgres://finops:finops_dev@postgres:5432/finops
    depends_on:
      postgres:
        condition: service_healthy
  ```

### `sql/init.sql` (~15 righe nuove)
- Aggiungere CREATE TABLE `cloud_config` e `extractor_runs` (idempotente con IF NOT EXISTS)

---

## K8s manifests (nuovi, reference)

```
k8s/
├── namespace.yaml
├── deployment-api.yaml      # API deployment (1 replica)
├── service-api.yaml         # ClusterIP + LoadBalancer
├── configmap.yaml           # Schedule, batch_size, log_level
├── secret-pg.yaml           # PG_DSN (se non usato da Helm)
└── cronjob-extractor.yaml   # (opzionale) esecuzione schedulata via K8s CronJob
```

I manifest K8s sono **reference** — si trasformano facilmente in Helm chart.
Non contengono segreti cloud (le credenziali arrivano via API dopo il deploy).

---

## Task list (ordine di implementazione)

### Fase 1: Fondamenta DB + API skeleton
- [ ] **T1.1** Creare `sql/migrations/001_cloud_config.sql` con tabelle `cloud_config` e `extractor_runs`
- [ ] **T1.2** Aggiungere CREATE TABLE idempotente in `sql/init.sql`
- [ ] **T1.3** Creare `api/__init__.py` e `api/db.py` (connection pool, init_db, helper query)
- [ ] **T1.4** Creare `api/models.py` (Pydantic schemas request/response)
- [ ] **T1.5** Creare `api/main.py` (FastAPI app, lifecycle, healthz, CORS)
- [ ] **T1.6** Aggiungere `fastapi` e `uvicorn` a `pyproject.toml`
- [ ] **T1.7** Test: avviare API, verificare `/healthz` e tabelle create

### Fase 2: CRUD configurazione
- [ ] **T2.1** Creare `api/routes/config.py` (GET list, POST create, GET by id, PUT, DELETE)
- [ ] **T2.2** Test: CRUD via curl/httpie, verificare persistenza DB
- [ ] **T2.3** Aggiungere validazione per-provider (campi required Azure vs GCP)

### Fase 3: Runner estrattori
- [ ] **T3.1** Creare `api/runner.py` (start_extractor, costruzione env vars da cloud_config)
- [ ] **T3.2** Creare `api/routes/extractors.py` (POST run, GET status, GET health)
- [ ] **T3.3** Modificare `extractors/azure_cost.py`: aggiungere `discover_azure_subscriptions_from_db()`
- [ ] **T3.4** Modificare `extractors/gcp_billing.py`: aggiungere `discover_gcp_configs_from_db()`
- [ ] **T3.5** Test: registrare config Azure via API → trigger run → verificare record in DB

### Fase 4: Auth proxy (device code)
- [ ] **T4.1** Creare `api/routes/auth.py` (device-code start + poll per Azure)
- [ ] **T4.2** Implementare polling Azure AD token lato API
- [ ] **T4.3** Al completamento, salvare config in `cloud_config` automaticamente
- [ ] **T4.4** Aggiungere endpoint GCP register (key file / ADC status)
- [ ] **T4.5** Test: device code flow completo via API → config salvata → run

### Fase 5: CLI → API integration
- [ ] **T5.1** Aggiungere `--api-url` a `config/auth.py` argparse
- [ ] **T5.2** Implementare `push_config_to_api()` in `config/auth.py`
- [ ] **T5.3** In `azure_auth_interactive()`: se `--api-url`, pusha dopo auth
- [ ] **T5.4** Aggiungere `--run` flag per trigger estrazione via API
- [ ] **T5.5** Test: `python -m config.auth azure --auto-select --api-url http://localhost:8000`

### Fase 6: Docker + Compose
- [ ] **T6.1** Creare `Dockerfile.api`
- [ ] **T6.2** Aggiornare `docker-compose.yml` con servizio `api`
- [ ] **T6.3** Test: `docker-compose up -d` → API + Postgres → curl CRUD → trigger run

### Fase 7: K8s manifests
- [ ] **T7.1** Creare `k8s/namespace.yaml`
- [ ] **T7.2** Creare `k8s/deployment-api.yaml`
- [ ] **T7.3** Creare `k8s/service-api.yaml`
- [ ] **T7.4** Creare `k8s/configmap.yaml`
- [ ] **T7.5** Creare `k8s/secret-pg.yaml` (solo PG_DSN)
- [ ] **T7.6** (Opzionale) Creare `k8s/cronjob-extractor.yaml`
- [ ] **T7.7** Test: `kubectl apply` → verificare pod + servizio

### Fase 8: Test end-to-end
- [ ] **T8.1** Test locale: CLI auth → API push → trigger run → record in DB
- [ ] **T8.2** Test Docker: compose up → API CRUD → run → record in DB
- [ ] **T8.3** Test K8s: deploy → API CRUD → run → record in DB
- [ ] **T8.4** Test device code flow via API
- [ ] **T8.5** Test error handling: credenziali errate, timeout, run fallita
- [ ] **T8.6** Verificare health tracking su `extractor_health` + `extractor_runs`

---

## Stima tempi per fase

| Fase | Tempo | Dipendenze |
|------|-------|------------|
| Fase 1: DB + API skeleton | 3-4h | Nessuna |
| Fase 2: CRUD config | 2-3h | Fase 1 |
| Fase 3: Runner estrattori | 3-4h | Fase 2 |
| Fase 4: Auth proxy (device code) | 2-3h | Fase 2 |
| Fase 5: CLI → API integration | 2-3h | Fase 2, 3 |
| Fase 6: Docker + Compose | 1-2h | Fase 1-5 |
| Fase 7: K8s manifests | 2-3h | Fase 6 |
| Fase 8: Test end-to-end | 2-3h | Fase 7 |
| **Totale** | **~17-25h** | |

---

## Note implementative

### Sicurezza
- `client_secret` in `cloud_config.config` va crittografato con Fernet (chiave in `ENCRYPTION_KEY` env var)
- Se `ENCRYPTION_KEY` non settata, fallback a plaintext + WARNING in log
- API senza auth per MVP; aggiungere API key / OIDC in seguito

### Subprocess isolation
- Ogni estrazione e un `subprocess.run()` con env vars isolati
- Il runner costruisce env vars dal `cloud_config.config` JSON:
  ```
  AZURE_TENANT_ID=... AZURE_CLIENT_ID=... AZURE_CLIENT_SECRET=...
  AZURE_SUBSCRIPTION_ID=... AZURE_SCOPE=resourcegroup
  AZURE_RESOURCE_GROUP=... PG_DSN=...
  ```
- Timeout default 30 minuti, configurabile
- Output catturato e salvato in `extractor_runs.log_output`

### Backward compatibility
- Gli estrattori funzionano ancora standalone (env vars + keyring)
- La priority chain diventa: env vars → keyring → DB `cloud_config`
- `config/auth.py` funziona ancora senza `--api-url` (modalita locale)
- `Dockerfile.extractor` invariato (batch mode per K8s CronJob)

### Scalabilita
- L'API e stateless (tutto in DB), puo scalare orizzontalmente
- Un'istanza alla volta lancia estrazioni (lock DB su `extractor_runs` per provider)
- Per multi-replica: usare advisory lock PG per coordinazione