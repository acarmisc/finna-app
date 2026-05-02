// API types based on FINNA-APP API specification

// --- Enums ---

export type Provider = 'azure' | 'gcp' | 'llm' | 'aws'
export type CredentialType = 'service_principal' | 'managed_identity' | 'cli' | 'device_code' | 'access_key' | 'assume_role'
export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled' | 'pending'
export type AlertSeverity = 'err' | 'warn' | 'ok'
export type AlertStatus = 'firing' | 'resolved' | 'pending' | 'all'

// --- Authentication DTOs ---

export interface TokenRequest {
  username: string
  password: string
}

export interface TokenResponse {
  token: string
  access_token?: string
  refresh_token?: string
}

export interface ErrorResponse {
  detail: string
  error?: string
  code?: string
}

// --- Configuration DTOs ---

export interface CloudConfigCreate {
  provider: 'azure' | 'gcp' | 'llm' | 'aws'
  name: string
  credential_type: CredentialType
  api_provider?: 'anthropic' | 'openai' | 'azure-openai'
  config: Record<string, unknown>
}

export interface CloudConfigUpdate {
  name?: string | null
  credential_type?: CredentialType | null
  config?: Record<string, unknown> | null
}

export interface CloudConfigResponse {
  id: string
  provider: Provider
  name: string
  credential_type: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ConfigTestResult {
  ok: boolean
  provider: 'azure' | 'gcp' | 'llm' | 'aws'
  latency_ms?: number
  checks: {
    auth: string
    scope?: string
    cost_management_api?: string
    sample_rows?: number
  }
  error?: string
}

export interface AzureConfigInput {
  tenant_id: string
  client_id: string
  client_secret?: string
  subscription_id: string
  resource_groups?: string[]
  scope?: 'resourcegroup' | 'subscription'
  environment?: 'prod' | 'staging' | 'dev'
  team?: string
}

export interface GCPConfigInput {
  project_id: string
  billing_account_id?: string
  bigquery_dataset?: string
  bigquery_table?: string
  environment?: 'prod' | 'staging' | 'dev'
  team?: string
}

export interface LLMConfigInput {
  api_provider: 'anthropic' | 'openai' | 'azure-openai'
  api_key: string
  base_url?: string
}

export interface AWSConfigInput {
  access_key_id?: string
  secret_access_key?: string
  region?: string
  role_arn?: string
}

// --- Project DTOs ---

export interface ProjectResponse {
  id: string
  name: string
  slug?: string
  owner?: string
  cost_center?: string
  budget_cap?: number | null
  mtd?: number
  tags?: Record<string, string>
  created_at?: string
  note?: string
  provider?: Provider
}

export interface ProjectCreate {
  name: string
  slug?: string
  owner?: string
  cost_center?: string
  budget_cap?: number
  tags?: Record<string, string>
  note?: string
}

export interface ProjectUpdate {
  name?: string
  owner?: string
  cost_center?: string
  budget_cap?: number
  tags?: Record<string, string>
  note?: string
}

// --- Cost DTOs ---

export interface CostRecord {
  id: string
  prov: Provider
  name: string
  sku: string
  mtd: number
  delta?: number
  prev?: number
  tags?: Record<string, string>
  date?: string
}

export interface CostListResponse {
  costs: CostRecord[]
  totals: Record<string, number>
  filtered: boolean
  startDate: string
  endDate: string
}

export interface CostTotalsResponse {
  totals: Record<string, number>
  startDate: string
  endDate: string
}

export interface CostBySkuResponse {
  costs: CostRecord[]
  totalRows: number
}

export interface CostDailyResponse {
  days: Array<{ date: string; azure?: number; gcp?: number; llm?: number; aws?: number }>
  startDate: string
  endDate: string
}

export interface CostExportParams {
  format: 'csv' | 'xlsx'
  startDate: string
  endDate: string
  providers?: Provider[]
}

// --- Alert DTOs ---

export interface AlertRecord {
  id: string
  title: string
  description: string
  severity: AlertSeverity
  resource: string
  service: string
  provider: string
  cost_impact: number
  first_seen: string
  last_seen: string
  is_acknowledged: boolean
  acknowledged_by?: string
  acknowledged_at?: string
  silenced_until?: string
}

export interface AlertListResponse {
  alerts: AlertRecord[]
  count: number
  total: number
}

export interface AlertStatsResponse {
  total: number
  by_severity: Record<string, number>
  by_provider: Record<string, number>
  acknowledged: number
  pending: number
  firing: number
  stats?: Array<{ status: string; severity: string; count: number }>
}

export interface AlertActionRequest {
  id: string
  duration?: number
  reason?: string
}

export interface AlertAcknowledgment {
  id: string
  acknowledged: boolean
  acknowledged_at: string
  acknowledged_by: string
}

export interface AlertSilencing {
  id: string
  silenced: boolean
  silenced_until?: string
}

// --- Extractor Registry DTOs ---

export interface ExtractorCreate {
  name: string
  provider: string
  extractor_type: string
  enabled?: boolean
  schedule?: string
  config_id?: string
}

export interface ExtractorUpdate {
  name?: string
  enabled?: boolean
  schedule?: string
  config_id?: string
}

export interface ExtractorResponse {
  id: string
  name: string
  provider: string
  extractor_type: string
  enabled: boolean
  schedule?: string
  config_id?: string
  status: 'idle' | 'running' | 'completed' | 'failed'
  last_run_id?: string
  last_run_at?: string
  created_at: string
  updated_at: string
}

export interface ExtractorListResponse {
  extractors: ExtractorResponse[]
  count: number
}

export interface ExtractorRunTriggerRequest {
  config_id?: string
  extractor_id?: string
}

export interface ExtractorRunTriggerResponse {
  run_id: string
  status: string
  extractor_id: string
}

export interface ExtractorRunResponse {
  id: string
  config_id: string
  extractor_id?: string
  provider: string
  extractor_type: string
  status: string
  started_at: string
  finished_at?: string
  records_extracted?: number
  error_message?: string
}

export interface ExtractorRunStatus {
  id: string
  provider: string
  extractor_type: string
  status: string
  started_at: string
  finished_at?: string
  records_extracted?: number
  error_message?: string
}

// --- Run DTOs ---

export interface RunListResponse {
  runs: Array<{
    id: string
    config_id: string
    extractor_type: string
    status: RunStatus
    started_at: string
    finished_at?: string
    records_extracted?: number
    error?: string
  }>
  count: number
}

// --- Configuration API DTOs ---

export interface ConfigResponse {
  id: string
  provider: Provider
  name: string
  credential_type: CredentialType
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ConfigListResponse {
  configs: ConfigResponse[]
  count: number
}

export interface ConfigTestRequest {
  provider: Provider
  credential_type: CredentialType
  config: Record<string, unknown>
}

// --- Settings API DTOs ---

export interface UserProfile {
  id: string
  email: string
  name?: string
  role: string
  org_id: string
  timezone: string
  locale: string
  created_at: string
}

export interface UserPreferences {
  theme: 'dark' | 'light' | 'system'
  default_window: string
  language: string
  notifications: {
    email_firing: boolean
    email_pending: boolean
    telegram_firing: boolean
    telegram_pending: boolean
    slack_firing: boolean
    slack_pending: boolean
    telegram_chat_id?: string
    slack_webhook?: string
  }
}

export interface ApiKey {
  id: string
  name: string
  prefix: string
  last_four: string
  created_at: string
  last_used_at?: string
  scopes: string[]
  active: boolean
}

export interface ApiKeyCreateRequest {
  name: string
  scopes: string[]
  expires_at?: string
}

export interface ApiKeyCreateResponse {
  id: string
  key: string
  name: string
  scopes: string[]
  created_at: string
}

// --- Health DTOs ---

export interface HealthResponse {
  status: 'ok' | 'degraded'
  api: string
  database: string
  cache?: string
  services?: Record<string, 'ok' | 'degraded' | 'error'>
}

export interface SystemStats {
  total_projects: number
  total_configs: number
  total_extractors: number
  active_runs: number
  alerts_firing: number
  storage_usage: number
  storage_limit: number
}

// --- UI Store Types ---

export interface ViewState {
  sidebarCollapsed: boolean
  theme: 'dark' | 'light' | 'system'
  dateRange: {
    start: Date | null
    end: Date | null
  }
}
