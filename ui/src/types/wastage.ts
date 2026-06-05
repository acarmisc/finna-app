// Wastage feature types — mirrors backend/app/api/models.py WastageFinding* schemas

export type WastageStatus = 'open' | 'acked' | 'resolved' | 'ignored'
export type WastageSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type WastageCategory = 'compute' | 'storage' | 'network' | 'database' | 'other'

export interface WastageFinding {
  finding_id: string
  provider: string
  account_id: string
  resource_group?: string | null
  region?: string | null
  resource_id: string
  resource_type: string
  rule_id: string
  severity: WastageSeverity
  category: WastageCategory
  estimated_monthly_usd: number
  currency: string
  evidence: Record<string, unknown>
  first_seen_at: string
  last_seen_at: string
  status: WastageStatus
  tags: Record<string, string>
}

export interface WastageFindingListResponse {
  data: WastageFinding[]
  total: number
  limit: number
  offset: number
  has_next: boolean
  has_prev: boolean
}

export interface WastageSummaryCategory {
  category: string
  finding_count: number
  total_monthly_usd: number
}

export interface WastageSummaryResponse {
  categories: WastageSummaryCategory[]
  total_monthly_usd: number
  total_finding_count: number
}

export interface WastageRule {
  id: string
  severity: WastageSeverity
  category: WastageCategory
  description: string
}

export interface WastageRulesResponse {
  rules: WastageRule[]
  count: number
}

export interface WastageScanRun {
  id: string
  provider: string
  started_at: string
  finished_at?: string | null
  status: 'running' | 'done' | 'error'
  findings_count?: number | null
  error?: string | null
}

export interface WastageScansResponse {
  scans: WastageScanRun[]
  count: number
}

export interface WastageFilterParams extends Record<string, unknown> {
  provider?: string
  severity?: string
  rule_id?: string
  status?: string
  account_id?: string
  limit?: number
  offset?: number
}
