# Feasibility Assessment: TUI-Based OAuth Authentication for Cloud Provider Extractors

**Date:** 2026-04-13  
**Scope:** Evaluate integrating OAuth device authorization flows into the finna-app TUI wizard (`config/wizard.py`) to replace manual credential entry for Azure and GCP extractors.

---

## 1. Azure OAuth via TUI

### 1.1 Device Authorization Grant Flow

Azure fully supports the [OAuth 2.0 Device Authorization Grant](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code) (RFC 8628). The flow is purpose-built for input-constrained devices like terminals:

1. **POST** to `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode` with `client_id` + `scope`
2. Response contains `user_code`, `verification_uri`, `expires_in` (default 15 min), `interval` (polling frequency)
3. TUI displays the URL and code; user authenticates in a browser on any device
4. Client polls `POST .../oauth2/v2.0/token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code` until success or expiry

**Required scopes for Cost Management API:**
- `https://management.azure.com/.default` — Azure Resource Manager (covers Cost Management)
- `offline_access` — to receive a refresh token (included by default in MSAL)

**Azure AD App Registration requirements:**
- Register a **public client** (no client secret) with redirect URI type "Mobile and desktop applications" → `http://localhost`
- API permissions: `UsageReports.Read.All` (Microsoft.CostManagement) — application or delegated
- For multi-tenant, use `/common` as the tenant path

### 1.2 Python Libraries

| Library | Device Code Support | Notes |
|---|---|---|
| `azure-identity` `DeviceCodeCredential` | Built-in, production-ready | Already in `requirements.txt`. Accepts `prompt_callback` for TUI integration. Handles token caching via `TokenCachePersistenceOptions`. |
| `msal` `PublicClientApplication.acquire_token_by_device_flow()` | Built-in, lower-level | Full control over polling. `initiate_device_flow()` returns the user_code/verification_uri dict. Already used internally by `azure-identity`. |

**Recommendation:** Use `azure-identity.DeviceCodeCredential` since it's already a dependency. The `prompt_callback` parameter is the key integration point:

```python
from azure.identity import DeviceCodeCredential

def tui_prompt(verification_uri, user_code, expires_on):
    console.print(Panel(
        f"1. Open: [cyan]{verification_uri}[/cyan]\n"
        f"2. Enter code: [bold]{user_code}[/bold]\n"
        f"   Expires: {expires_on:%H:%M:%S}",
        title="Azure Authentication", border_style="blue"
    ))

credential = DeviceCodeCredential(
    client_id="<app-registration-id>",
    tenant_id="<tenant>",
    prompt_callback=tui_prompt,
)
```

### 1.3 Token Refresh

- `DeviceCodeCredential` handles refresh automatically via MSAL's internal `TokenCache`
- With `cache_persistence_options=TokenCachePersistenceOptions()`, tokens persist across sessions using the OS keyring (via MSAL's persistence layer)
- Access tokens expire in ~60 min; refresh tokens are valid for 90 days (revocable by admin)
- Silent re-authentication works as long as the refresh token is valid — no re-prompt needed

### 1.4 Migration from ClientSecretCredential

Current code in `extractors/azure_cost.py:505-511`:
```python
credential = ClientSecretCredential(
    tenant_id=_env("AZURE_TENANT_ID"),
    client_id=_env("AZURE_CLIENT_ID"),
    client_secret=_env("AZURE_CLIENT_SECRET"),
)
```

This would become:
```python
credential = DeviceCodeCredential(
    client_id=_env("AZURE_CLIENT_ID"),
    tenant_id=_env("AZURE_TENANT_ID"),
    prompt_callback=tui_prompt,
    cache_persistence_options=TokenCachePersistenceOptions(),
)
```

The credential object produces the same `TokenCredential` interface — no changes needed to `CostManagementClient` usage.

---

## 2. GCP OAuth via TUI

### 2.1 The Challenge

GCP is architecturally different from Azure:
- **Primary auth pattern:** Service account keys (what the project currently uses)
- **`gcloud auth login`** uses OAuth2 browser-based flow (auth code grant, not device flow)
- **ADC (Application Default Credentials)** chains: `GOOGLE_APPLICATION_CREDENTIALS` env → well-known file → `gcloud` user credentials → compute metadata

GCP does **not** natively support a first-class device authorization grant flow for end-user accounts. However, there are viable paths:

### 2.2 Option A: OAuth2 Out-of-Band (OOB) / Device-Style Flow

Google Cloud OAuth supports `response_type=code` with `redirect_uri=urn:ietf:wg:oauth:2.0:oob` (out-of-band) or `http://localhost` with a local server. `google-auth-library-python` provides:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secrets.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"],
)
credentials = flow.run_local_server(port=0)  # Opens browser, listens on localhost
```

**TUI limitation:** `run_local_server()` opens a browser and spins up a temporary HTTP server on localhost. This is not a pure terminal flow. However:
- `InstalledAppFlow.run_console()` existed as a deprecated OOB flow (Google [disabled OOB](https://developers.google.com/identity/protocols/oauth2/resources/oob-migration) in 2022 for security)
- You can still manually construct a device-code-like flow by using Google's OAuth2 endpoints directly and polling, but Google does not officially support RFC 8628

### 2.3 Option B: Delegate to `gcloud auth login`

The simplest and most reliable approach:
1. TUI detects no ADC configured
2. TUI prompts: "Run `gcloud auth login` in another terminal, then press Enter"
3. After user completes browser-based auth, ADC picks up credentials automatically
4. `google.cloud.bigquery.Client()` (already in use at `extractors/gcp_billing.py:345`) works with ADC — **zero code changes to extractors**

```python
import subprocess

def ensure_gcp_auth():
    from google.auth import default
    try:
        creds, project = default()
        if creds and creds.valid:
            return creds, project
    except google.auth.exceptions.DefaultCredentialsError:
        pass
    
    proceed = questionary.confirm(
        "No GCP credentials found. Run 'gcloud auth login' now?",
        default=True,
    ).ask()
    if proceed:
        subprocess.run(["gcloud", "auth", "login"])
        creds, project = default()
        return creds, project
    raise EnvironmentError("GCP authentication required")
```

### 2.4 Option C: Custom Device Flow Implementation

Google's OAuth2 endpoints can be used with a manually-implemented polling flow, but this requires:
- A registered OAuth client (web or desktop type)
- Managing the token lifecycle yourself
- No official SDK support for device code flow

This is fragile and not recommended.

### 2.5 Recommendation for GCP

**Use Option B (gcloud delegation).** It is the most robust, requires no new dependencies, and aligns with how `gh auth login` and `databricks-cli` handle authentication. The `google-cloud-bigquery` library already uses ADC, so no extractor code changes are needed. The TUI simply orchestrates the `gcloud` CLI.

---

## 3. TUI Integration Design

### 3.1 Wizard Flow Changes

Current flow in `config/wizard.py`:
```
ask_providers() → ask_gcp() | ask_azure() → build_config()
```

Proposed enhanced flow:
```
ask_providers()
  → for each provider:
      ask_auth_method()  # "oauth_device" | "manual" | "existing"
      if oauth_device:
          run_device_flow()  # with polling + progress
      elif manual:
          ask_*_manual()     # current behavior
      elif existing:
          validate_existing_credentials()
```

### 3.2 Device Flow UX Pattern

The device code flow fits naturally into a `questionary`/`rich` TUI:

```python
import time
from rich.progress import Progress, SpinnerColumn, TextColumn

def run_azure_device_flow(tenant_id: str, client_id: str):
    console.rule("[bold blue]Azure OAuth Authentication[/bold blue]")
    
    auth_method = questionary.select(
        "Azure authentication method:",
        choices=["OAuth (browser login — recommended)", "Manual (service principal)"],
    ).ask()
    
    if auth_method and "OAuth" in auth_method:
        credential = DeviceCodeCredential(
            client_id=client_id,
            tenant_id=tenant_id,
            prompt_callback=lambda uri, code, exp: console.print(Panel(
                f"[bold]To sign in:[/bold]\n\n"
                f"  1. Open [cyan link={uri}]{uri}[/cyan]\n"
                f"  2. Enter code: [bold yellow]{code}[/bold]\n\n"
                f"  Code expires at {exp:%H:%M:%S}",
                title="Azure Device Login", border_style="blue"
            )),
            cache_persistence_options=TokenCachePersistenceOptions(),
        )
        
        # This call blocks until user completes auth or timeout
        token = credential.get_token("https://management.azure.com/.default")
        console.print("[bold green]Azure authentication successful![/bold green]")
        return credential
```

The `prompt_callback` is called once by the credential. The underlying `acquire_token_by_device_flow` in MSAL handles all polling asynchronously. The TUI thread blocks but remains responsive — the user sees the instruction panel and authenticates in their browser.

### 3.3 Polling Status Display

For a richer UX during polling, use `rich.live.Live` with a spinner:

```python
from rich.live import Live
from rich.text import Text

def run_device_flow_with_status():
    status = Text("Waiting for browser authentication...")
    with Live(status, refresh_per_second=4, console=console):
        result = credential.get_token("https://management.azure.com/.default")
    status = Text("Authenticated successfully!", style="bold green")
    console.print(status)
```

### 3.4 Timeout Handling

- Azure device codes expire in 15 min (default)
- `DeviceCodeCredential(timeout=...)` accepts a timeout in seconds
- If the user doesn't complete auth in time, `ClientAuthenticationError` is raised
- The wizard should catch this and offer retry or fallback to manual entry:

```python
try:
    credential = DeviceCodeCredential(...)
    token = credential.get_token(...)
except ClientAuthenticationError:
    retry = questionary.confirm(
        "Authentication timed out. Retry or switch to manual entry?",
        default=True,
    ).ask()
```

---

## 4. Token Storage

### 4.1 Options Comparison

| Method | Security | Persistence | Cross-platform | Docker-compatible |
|---|---|---|---|---|
| **OS Keyring** (via `keyring` or MSAL persistence) | High — OS-level encryption | Yes | macOS Keychain, Linux Secret Service, Windows Credential Locker | No — headless containers lack keyring daemons |
| **Encrypted file** (Fernet) | Medium — key management burden | Yes | Yes | Yes |
| **Environment variables** | Low — visible in /proc, process listings | No (ephemeral) | Yes | Yes |
| **`.env` file** (current approach) | Low — plaintext on disk | Yes | Yes | Yes |

### 4.2 Recommendation: Tiered Strategy

**Primary (developer workstation):** OS keyring via `azure-identity`'s `TokenCachePersistenceOptions`. This is the default when using `DeviceCodeCredential` with `cache_persistence_options`. MSAL uses `msal_extensions` which internally uses `keyring`.

**Secondary (container/CI):** Encrypted file or env vars. The current `.env` file approach works for container-deployed extractors. The wizard should support both modes:

```
if running_interactively() and keyring_available():
    # Use OS keyring (transparent to user)
    credential = DeviceCodeCredential(
        cache_persistence_options=TokenCachePersistenceOptions(),
    )
else:
    # Container mode: store refresh token encrypted or use env vars
    credential = ClientSecretCredential(...)  # current approach
```

### 4.3 New Dependency: `keyring`

Add `keyring>=25.0` to `requirements.txt` for OS-agnostic secure token storage. Already a mature, production-stable package (25.x series). MSAL's `msal_extensions` also depends on it.

For Docker/headless: Keyring can be disabled via `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`, and tokens fall through to env vars or encrypted files.

---

## 5. Security Considerations

### 5.1 OAuth Tokens vs Service Account Keys

| Aspect | Service Account Key (current) | OAuth Device Flow (proposed) |
|---|---|---|
| **Blast radius if leaked** | Full — key grants access until rotation | Limited — tokens expire (access: ~1hr, refresh: ~90 days, revocable) |
| **Rotation** | Manual, often never rotated | Automatic via refresh tokens; admin can revoke instantly |
| **Least privilege enforcement** | Key inherits all SA permissions | User's delegated permissions; can be scoped per API |
| **Audit trail** | Key usage is opaque | User-bound; Entra ID logs who authenticated |
| **Storage risk** | JSON file on disk (often committed accidentally) | OS keyring (encrypted) or short-lived token |

**Verdict:** OAuth device flow is strictly more secure than service account keys for interactive/onboarding use.

### 5.2 GCP: Service Account Keys vs User Credentials

- Service accounts represent a workload, not a user — appropriate for automation (extractors)
- User OAuth credentials represent a person — appropriate for initial setup but not for long-running jobs
- **Best practice:** Use OAuth/device flow in the TUI during wizard setup to obtain initial credentials, then create a scoped service account for the extractor automatically

### 5.3 Least Privilege

- **Azure:** Register a dedicated App Registration with `Microsoft.CostManagement/usageReports/read` only. Do not use the Azure CLI's default client ID (`04b07795-...`).
- **GCP:** When using `gcloud auth login`, add `--scopes=https://www.googleapis.com/auth/cloud-billing.readonly`. For service accounts created for extractors, grant only `roles/bigquery.dataViewer` on the billing dataset.

### 5.4 Refresh Token Revocation

- Azure admins can revoke refresh tokens via Conditional Access policies or `Revoke-AzureADUserRefreshToken`
- GCP admins can revoke via Admin Console → Security → Users → revoke OAuth tokens
- Both platforms support token revocation without requiring re-registration

---

## 6. Existing Libraries and Patterns

### 6.1 How Popular CLIs Handle Terminal OAuth

| CLI | Approach | Flow Type |
|---|---|---|
| `az login` | Opens browser; falls back to device code if no browser | Auth code → device code |
| `gcloud auth login` | Opens browser; local server on localhost:808X | Auth code grant |
| `gh auth login` | Opens browser; local server + device code fallback | Auth code + device code |
| `databricks-cli` | Opens browser; falls back to device code | Auth code → device code |
| `aws sso login` | Opens browser; device code as fallback | Auth code → device code |

**Common pattern:** All attempt browser-based auth code flow first (opening a localhost redirect server), with device code as a fallback for headless/SSH environments. The finna-app wizard should follow this same pattern.

### 6.2 Relevant Python Libraries

| Library | Purpose | Status |
|---|---|---|
| `azure-identity>=1.14` | Azure auth (DeviceCodeCredential, TokenCachePersistenceOptions) | Already in requirements.txt |
| `msal` | Lower-level MSAL (used internally by azure-identity) | Transitive dependency |
| `msal_extensions` | Persistent token cache via OS keyring | Transitive dep of azure-identity |
| `keyring>=25.0` | Cross-platform OS keyring access | **New addition needed** |
| `google-auth-oauthlib` | GCP OAuth2 flow (InstalledAppFlow) | New addition (optional) |
| `google-auth` | ADC and credential management | Transitive dep of google-cloud-bigquery |

### 6.3 Patterns from `azure-identity`

`DeviceCodeCredential` with `prompt_callback` is the canonical TUI integration pattern:

```python
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions

credential = DeviceCodeCredential(
    client_id=app_reg_id,
    tenant_id=tenant_id,
    prompt_callback=lambda uri, code, exp: print(f"Visit {uri} and enter {code}"),
    cache_persistence_options=TokenCachePersistenceOptions(name="finna-app"),
)
```

This single object handles: device code acquisition, user prompting, polling, token retrieval, caching, and silent refresh.

---

## 7. Feasibility Verdict

### Azure: **FEASIBLE — Low Risk, High Value**

- `azure-identity.DeviceCodeCredential` already in dependencies
- `prompt_callback` provides clean TUI integration
- `TokenCachePersistenceOptions` handles token persistence via OS keyring
- No extractor code changes — `TokenCredential` interface is unchanged
- The only new requirement: Azure AD App Registration (public client type)

### GCP: **FEASIBLE — Medium Risk, Moderate Value**

- No native device code flow; must delegate to `gcloud auth login`
- ADC integration works automatically with `google.cloud.bigquery.Client()`
- Value is lower since service account keys are the appropriate pattern for automated extractors
- `google-auth-oauthlib.InstalledAppFlow.run_local_server()` works if a browser is available
- Best ROI: detect missing ADC → prompt user to run `gcloud auth login` → validate

### Recommended Implementation Phases

| Phase | Scope | Effort |
|---|---|---|
| **P1** | Azure: Add `DeviceCodeCredential` option to wizard, app registration docs | 2-3 days |
| **P2** | GCP: Add `gcloud auth login` detection + delegation to wizard | 1-2 days |
| **P3** | Token storage: Add `keyring` dependency, integrate `TokenCachePersistenceOptions` | 1 day |
| **P4** | Schema update: Add `auth_method` field to `AzureSubscriptionConfig` / `GCPConfig` | 1 day |
| **P5** | Extractor credential abstraction: Support both `ClientSecretCredential` and `DeviceCodeCredential` at runtime | 1 day |

### Blocking Dependencies

- **Azure:** Azure AD App Registration must be created (public client, Cost Management API permissions)
- **GCP:** None — `gcloud` CLI must be installed (already standard for GCP users)
- **Both:** Appropriate OAuth scopes must be documented for users

### Risks

| Risk | Mitigation |
|---|---|
| Headless Docker containers can't do device flow | Keep manual credential entry as fallback; device flow is for onboarding only |
| GCP has no device code flow | Delegate to `gcloud auth login` which uses browser auth code flow |
| OS keyring unavailable in CI/CD | Fall back to env vars or encrypted file; use `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` |
| Azure device code expires before user completes | `DeviceCodeCredential(timeout=...)` + retry prompt in wizard |
| Multiple tenants/tenancies | Prompt for tenant_id in wizard; `DeviceCodeCredential(tenant_id=...)` per subscription |