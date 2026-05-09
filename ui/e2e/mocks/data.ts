/**
 * Mock data for e2e tests.
 * Provides realistic responses for every backend endpoint used by the UI.
 */

export const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciJ9.mock'

export const mockDashboardStats = (range = 'mtd') => ({
  totals: { total: 12450.32, azure: 5432.10, gcp: 4567.89, llm: 2450.33 },
  daily: [
    { date: '2024-01-01', azure: 120.5, gcp: 98.2, llm: 45.1 },
    { date: '2024-01-02', azure: 135.0, gcp: 102.3, llm: 50.0 },
    { date: '2024-01-03', azure: 110.2, gcp: 95.1, llm: 42.5 },
    { date: '2024-01-04', azure: 140.0, gcp: 110.0, llm: 55.0 },
    { date: '2024-01-05', azure: 130.5, gcp: 105.5, llm: 48.0 },
  ],
  alertStats: { firing: 2, ack: 1, resolved: 5, by_severity: { err: 1, warn: 1 } },
})

export const mockProjects = [
  { id: 'p1', name: 'Platform Infra', slug: 'platform-infra', owner: 'sre', cost_center: 'eng', budget_cap: 5000, mtd: 3200.50, tags: { env: 'prod' }, created: '2024-01-01T00:00:00Z', note: 'Core platform', provider: 'azure' },
  { id: 'p2', name: 'ML Pipeline', slug: 'ml-pipeline', owner: 'ml-team', cost_center: 'ml', budget_cap: 8000, mtd: 5400.20, tags: { env: 'prod' }, created: '2024-01-15T00:00:00Z', note: 'Training jobs', provider: 'gcp' },
  { id: 'p3', name: 'Dev Sandbox', slug: 'dev-sandbox', owner: 'devs', cost_center: 'eng', budget_cap: 500, mtd: 120.00, tags: { env: 'dev' }, created: '2024-02-01T00:00:00Z', note: '', provider: 'azure' },
]

export const mockCosts = {
  costs: [
    { id: 'c1', prov: 'azure', project_id: 'p1', name: 'Platform Infra', sku: 'Virtual Machines', mtd: 1200.50, delta: 5.2, prev: 1140.00, tags: { env: 'prod' }, date: '2024-01-05' },
    { id: 'c2', prov: 'gcp', project_id: 'p2', name: 'ML Pipeline', sku: 'Vertex AI', mtd: 2100.00, delta: -2.1, prev: 2145.00, tags: { env: 'prod' }, date: '2024-01-05' },
    { id: 'c3', prov: 'llm', project_id: 'p2', name: 'ML Pipeline', sku: 'Claude API', mtd: 450.33, delta: 12.0, prev: 402.00, tags: {}, date: '2024-01-04' },
  ],
  totals: { azure: 5432.10, gcp: 4567.89, llm: 2450.33 },
  filtered: true,
  startDate: '2024-01-01T00:00:00',
  endDate: '2024-01-31T23:59:59',
  window: 'mtd',
  data: [
    { id: 'c1', prov: 'azure', project_id: 'p1', name: 'Platform Infra', sku: 'Virtual Machines', mtd: 1200.50, delta: 5.2, prev: 1140.00, tags: { env: 'prod' }, date: '2024-01-05' },
    { id: 'c2', prov: 'gcp', project_id: 'p2', name: 'ML Pipeline', sku: 'Vertex AI', mtd: 2100.00, delta: -2.1, prev: 2145.00, tags: { env: 'prod' }, date: '2024-01-05' },
    { id: 'c3', prov: 'llm', project_id: 'p2', name: 'ML Pipeline', sku: 'Claude API', mtd: 450.33, delta: 12.0, prev: 402.00, tags: {}, date: '2024-01-04' },
  ],
  total: 3,
  page: 1,
  page_size: 50,
  has_next: false,
  has_prev: false,
}

export const mockAlerts = {
  alerts: [
    { id: 'a1', status: 'firing', severity: 'err', description: 'Azure VM cost spike > 20%', rule: 'cost-spike-vm', project: 'Platform Infra', triggered_at: '2024-01-05T10:00:00Z', cost_impact: 340.00, resource: 'vm-scale-set', service: 'Virtual Machines', provider: 'azure', is_acknowledged: false, first_seen: '2024-01-05T10:00:00Z', last_seen: '2024-01-05T10:00:00Z' },
    { id: 'a2', status: 'firing', severity: 'warn', description: 'LLM usage approaching budget', rule: 'llm-budget', project: 'ML Pipeline', triggered_at: '2024-01-04T08:00:00Z', cost_impact: 120.00, resource: 'claude-api', service: 'Claude API', provider: 'llm', is_acknowledged: false, first_seen: '2024-01-04T08:00:00Z', last_seen: '2024-01-05T09:00:00Z' },
    { id: 'a3', status: 'ack', severity: 'warn', description: 'GCP storage cost increase', rule: 'storage-increase', project: 'ML Pipeline', triggered_at: '2024-01-03T12:00:00Z', cost_impact: 45.00, resource: 'gcs-bucket', service: 'Cloud Storage', provider: 'gcp', is_acknowledged: true, first_seen: '2024-01-03T12:00:00Z', last_seen: '2024-01-03T12:00:00Z' },
  ],
  count: 3,
  data: [
    { id: 'a1', status: 'firing', severity: 'err', description: 'Azure VM cost spike > 20%', rule: 'cost-spike-vm', project: 'Platform Infra', triggered_at: '2024-01-05T10:00:00Z', cost_impact: 340.00, resource: 'vm-scale-set', service: 'Virtual Machines', provider: 'azure', is_acknowledged: false, first_seen: '2024-01-05T10:00:00Z', last_seen: '2024-01-05T10:00:00Z' },
    { id: 'a2', status: 'firing', severity: 'warn', description: 'LLM usage approaching budget', rule: 'llm-budget', project: 'ML Pipeline', triggered_at: '2024-01-04T08:00:00Z', cost_impact: 120.00, resource: 'claude-api', service: 'Claude API', provider: 'llm', is_acknowledged: false, first_seen: '2024-01-04T08:00:00Z', last_seen: '2024-01-05T09:00:00Z' },
    { id: 'a3', status: 'ack', severity: 'warn', description: 'GCP storage cost increase', rule: 'storage-increase', project: 'ML Pipeline', triggered_at: '2024-01-03T12:00:00Z', cost_impact: 45.00, resource: 'gcs-bucket', service: 'Cloud Storage', provider: 'gcp', is_acknowledged: true, first_seen: '2024-01-03T12:00:00Z', last_seen: '2024-01-03T12:00:00Z' },
  ],
  total: 3,
  page: 1,
  page_size: 50,
  has_next: false,
  has_prev: false,
}

export const mockAlertStats = {
  total: 3,
  by_status: { firing: 2, ack: 1, resolved: 5 },
  by_severity: { critical: 1, warning: 2, info: 0 },
  stats: [],
}

export const mockConfigs = {
  data: [
    { id: 'cfg1', provider: 'azure', name: 'Azure Prod', credential_type: 'spn', service_category: 'spn', region: 'westeurope', last_test: true, last_test_at: '2024-01-05T00:00:00Z', err: null, last_updated: '2024-01-05T00:00:00Z' },
    { id: 'cfg2', provider: 'gcp', name: 'GCP ML', credential_type: 'sa', service_category: 'sa', region: 'us-central1', last_test: true, last_test_at: '2024-01-04T00:00:00Z', err: null, last_updated: '2024-01-04T00:00:00Z' },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  has_next: false,
  has_prev: false,
}

export const mockExtractors = {
  data: [
    { id: 'ext1', name: 'azure-costs', provider: 'azure', config_id: 'cfg1', config_name: 'Azure Prod', enabled: true, schedule: '0 * * * *', last_run: '2024-01-05T00:00:00Z', status: 'idle', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-05T00:00:00Z' },
    { id: 'ext2', name: 'gcp-costs', provider: 'gcp', config_id: 'cfg2', config_name: 'GCP ML', enabled: true, schedule: '0 */6 * * *', last_run: '2024-01-04T18:00:00Z', status: 'idle', created_at: '2024-01-02T00:00:00Z', updated_at: '2024-01-04T18:00:00Z' },
  ],
  count: 2,
  total: 2,
  page: 1,
  page_size: 50,
  has_next: false,
  has_prev: false,
}

export const mockExtractorRuns = {
  runs: [
    { id: 'run1', run_id: 'run1', extractor_type: 'azure-costs', provider: 'azure', status: 'success', records_extracted: 1240, started_at: '2024-01-05T00:00:00Z', finished_at: '2024-01-05T00:02:30Z' },
    { id: 'run2', run_id: 'run2', extractor_type: 'gcp-costs', provider: 'gcp', status: 'success', records_extracted: 890, started_at: '2024-01-04T18:00:00Z', finished_at: '2024-01-04T18:01:45Z' },
    { id: 'run3', run_id: 'run3', extractor_type: 'azure-costs', provider: 'azure', status: 'failed', records_extracted: 0, started_at: '2024-01-04T12:00:00Z', finished_at: '2024-01-04T12:00:10Z' },
  ],
}
