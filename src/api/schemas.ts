import { z } from 'zod/v4'

// --- Auth ---
export const TokenResponseSchema = z.object({
  token: z.string(),
  access_token: z.string().optional(),
})

// --- Dashboard ---
export const DashboardTotalsSchema = z.object({
  mtd: z.number(),
  delta: z.number(),
  azure: z.object({ mtd: z.number(), delta: z.number() }),
  gcp: z.object({ mtd: z.number(), delta: z.number() }),
  llm: z.object({ mtd: z.number(), delta: z.number() }),
})

export const DailyRecordSchema = z.object({
  label: z.string(),
  value: z.number(),
})

export const DailyCostSchema = z.object({
  azure: z.array(DailyRecordSchema),
  gcp: z.array(DailyRecordSchema),
  llm: z.array(DailyRecordSchema),
})

export const TopProjectSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  value: z.number(),
})

export const ExtractorRunSchema = z.object({
  run_id: z.string(),
  extractor_type: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  status: z.enum(['running', 'completed', 'failed']),
  records_extracted: z.number(),
  duration: z.string(),
  started_at: z.string(),
})

// --- Projects ---
export const ProjectSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  owner: z.string(),
  cost_center: z.string(),
  budget_cap: z.number(),
  mtd: z.number(),
  tags: z.array(z.string()),
})

export const ProjectDetailSchema = ProjectSchema.extend({
  note: z.string().optional().nullable(),
  skus: z.array(z.object({
    sku: z.string(),
    mtd: z.number(),
    prev: z.number(),
    delta: z.number(),
  })),
})

// --- Costs ---
export const CostRecordSchema = z.object({
  id: z.string(),
  prov: z.enum(['azure', 'gcp', 'llm']),
  name: z.string(),
  sku: z.string(),
  mtd: z.number(),
  prev: z.number(),
  delta: z.number(),
})

export const CostBySkuGroupSchema = z.object({
  sku: z.string(),
  providers: z.array(z.enum(['azure', 'gcp', 'llm'])),
  count: z.number(),
  mtd: z.number(),
  prev: z.number(),
})

export const CostsListResponseSchema = z.object({
  rows: z.array(CostRecordSchema),
  grandTotal: z.number(),
  grandPrev: z.number(),
})

export const CostsBySkuResponseSchema = z.object({
  bySku: z.array(CostBySkuGroupSchema),
})

// --- Alerts ---
export const AlertStatsSchema = z.object({
  total: z.number(),
  firing: z.number(),
  pending: z.number(),
  ok: z.number(),
})

export const AlertSchema = z.object({
  id: z.string(),
  name: z.string(),
  target_type: z.string(),
  target_name: z.string(),
  metric: z.string(),
  condition: z.string(),
  threshold: z.number(),
  current_value: z.number(),
  status: z.enum(['firing', 'pending', 'ok']),
  provider: z.enum(['azure', 'gcp', 'llm']),
  created_at: z.string(),
})

// --- Cloud Configs ---
export const CloudConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  credential_type: z.string(),
  created_at: z.string(),
  last_test: z.enum(['completed', 'running', 'failed']),
  last_test_at: z.string(),
  err: z.string().nullable(),
  // Azure specific
  tenant_id: z.string().optional(),
  subscription_id: z.string().optional(),
  // GCP specific
  project_id: z.string().optional(),
})

// --- Run History ---
export const RunHistoryRecordSchema = z.object({
  run_id: z.string(),
  extractor_type: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  status: z.enum(['running', 'completed', 'failed']),
  records_extracted: z.number(),
  duration: z.string(),
  started_at: z.string(),
  finished_at: z.string(),
})

// --- Data Sources ---
export const DataSourceSchema = z.object({
  id: z.string(),
  name: z.string(),
  provider: z.enum(['azure', 'gcp', 'llm']),
  type: z.string(),
  scope: z.string(),
  config: z.string(),
  config_id: z.string(),
  extractor: z.string(),
  schedule: z.string(),
  last_run: z.object({
    status: z.enum(['running', 'completed', 'failed']),
    at: z.string(),
    records: z.number(),
  }),
  health: z.enum(['healthy', 'degraded', 'unhealthy']),
  records_total: z.string(),
})

// --- Settings ---
export const UserProfileSchema = z.object({
  name: z.string(),
  email: z.string(),
  timezone: z.string(),
  currency: z.string(),
  date_format: z.string(),
})

export const NotificationPrefsSchema = z.object({
  email_firing: z.boolean(),
  email_pending: z.boolean(),
  telegram_firing: z.boolean(),
  telegram_pending: z.boolean(),
  slack_firing: z.boolean(),
  slack_pending: z.boolean(),
  telegram_chat_id: z.string(),
  slack_webhook: z.string(),
})

export const ApiKeySchema = z.object({
  name: z.string(),
  key: z.string(),
  created: z.string(),
  last: z.string(),
  scopes: z.array(z.string()),
})

// --- Utils ---
export const PaginationSchema = z.object({
  page: z.number().optional(),
  limit: z.number().optional(),
  total: z.number(),
})
