import type { Connection, CostRecord, Run, Alert, DayData, FinProject, AppData, Resource } from '../types';

const FIN_PROJECTS: FinProject[] = [
  { id: 'p1', name: 'data-platform', slug: 'data-platform', owner: 'Andrea C.', costCenter: 'Engineering', budgetCap: 15000, mtd: 8412, tags: { env: 'prod', team: 'data' }, created: '2025-01-15', note: 'Main analytics platform' },
  { id: 'p2', name: 'ml-inference', slug: 'ml-inference', owner: 'Sara K.', costCenter: 'AI/ML', budgetCap: 25000, mtd: 12340, tags: { env: 'prod', team: 'ml' }, created: '2025-02-01', note: 'LLM inference workloads' },
  { id: 'p3', name: 'staging', slug: 'staging', owner: 'DevOps', costCenter: 'Engineering', budgetCap: 5000, mtd: 1890, tags: { env: 'staging' }, created: '2025-03-10', note: 'Staging environment' },
];

const CONNECTIONS: Connection[] = [
  { id: 'c1', prov: 'azure', name: 'Azure EA', scope: '/subscriptions/sub-1', status: 'ok', lastRun: '2025-11-14T02:00Z', rows: '1.2M', auth: 'client_secret', expires: '2026-06-01', projectId: 'p1' },
  { id: 'c2', prov: 'gcp', name: 'GCP Billing', scope: 'projects/data-platform', status: 'ok', lastRun: '2025-11-14T02:00Z', rows: '890K', auth: 'adc', expires: '2026-01-01', projectId: 'p1' },
  { id: 'c3', prov: 'azure', name: 'Azure ML', scope: '/subscriptions/sub-2', status: 'ok', lastRun: '2025-11-14T02:00Z', rows: '340K', auth: 'device_code', expires: '2026-04-01', projectId: 'p2' },
  { id: 'c4', prov: 'gcp', name: 'GCP Staging', scope: 'projects/staging', status: 'warn', lastRun: '2025-11-13T02:00Z', rows: '12K', auth: 'adc', expires: '2026-01-01', projectId: 'p3', note: 'Partial data — BigQuery export lag' },
  { id: 'c5', prov: 'llm', name: 'OTel Gateway', scope: 'http://otel-collector:4317', status: 'ok', lastRun: '2025-11-14T02:00Z', rows: '45K', auth: 'none', expires: 'never', projectId: 'p2' },
  { id: 'c6', prov: 'azure', name: 'Azure Staging', scope: '/subscriptions/sub-3', status: 'err', lastRun: '2025-11-12T02:00Z', rows: '0', auth: 'client_secret', expires: '2025-10-01', err: 'AADSTS700082: The refresh token has expired', projectId: 'p3' },
  { id: 'c7', prov: 'gcp', name: 'GCP ML', scope: 'projects/ml-inference', status: 'ok', lastRun: '2025-11-14T02:00Z', rows: '220K', auth: 'service_account', expires: '2026-12-01', projectId: 'p2' },
];

const RESOURCES_BY_CONN: Record<string, Resource[]> = {
  c1: [
    { id: 'r1', name: 'vm-analytics-01', type: 'Virtual Machine', native: 'Standard_D4s_v3', mtd: 420.5, tags: { env: 'prod', service: 'analytics' } },
    { id: 'r2', name: 'storage-logs', type: 'Storage Account', native: 'LRS Hot', mtd: 85.2, tags: { env: 'prod', service: 'logging' } },
  ],
  c2: [
    { id: 'r3', name: 'bq-billing-export', type: 'BigQuery', native: 'US multi-region', mtd: 210.0, tags: { env: 'prod', service: 'billing' } },
  ],
};

const COSTS: CostRecord[] = [
  { prov: 'azure', name: 'vm-analytics-01', sku: 'Standard_D4s_v3', mtd: 420.5, delta: 12.3, prev: 374.5 },
  { prov: 'gcp', name: 'bq-billing-export', sku: 'BigQuery Analysis', mtd: 210.0, delta: -5.2, prev: 221.5 },
  { prov: 'azure', name: 'storage-logs', sku: 'Blob Storage LRS Hot', mtd: 85.2, delta: 8.1, prev: 78.8 },
  { prov: 'llm', name: 'gpt-4o', sku: 'OpenAI API', mtd: 1200.0, delta: 45.0, prev: 827.6 },
  { prov: 'gcp', name: 'gke-cluster-01', sku: 'GKE Compute', mtd: 340.0, delta: -2.1, prev: 347.3 },
  { prov: 'llm', name: 'claude-3.5-sonnet', sku: 'Anthropic API', mtd: 890.0, delta: 22.0, prev: 729.5 },
];

const RUNS: Run[] = [
  { id: 'run1', type: 'azure_cost', prov: 'azure', status: 'success', started: '02:00 UTC', dur: '45s', rows: 26 },
  { id: 'run2', type: 'gcp_billing', prov: 'gcp', status: 'success', started: '02:01 UTC', dur: '32s', rows: 18 },
  { id: 'run3', type: 'exchange_rates', prov: 'ecb', status: 'success', started: '16:05 UTC', dur: '3s', rows: 34 },
  { id: 'run4', type: 'azure_cost', prov: 'azure', status: 'running', started: '02:00 UTC', dur: '12s', rows: 0 },
  { id: 'run5', type: 'gcp_billing', prov: 'gcp', status: 'failed', started: '01:55 UTC', dur: '8s', rows: 0, err: 'BigQuery timeout' },
];

const ALERTS: Alert[] = [
  { id: 'a1', severity: 'err', title: 'Azure token expired', body: 'AADSTS700082: refresh token expired for Azure Staging', rule: 'SELECT * FROM extractor_health\nWHERE status = \'failed\' AND age > interval \'24 hours\'', firing: '2 hours ago', channels: ['email', 'slack'] },
  { id: 'a2', severity: 'warn', title: 'Budget threshold 85%', body: 'data-platform MTD ($8.4K) is 56% of $15K cap', rule: 'SELECT project_id, mtd_spend/budget_cap as pct\nFROM project_budgets WHERE pct > 0.8', firing: '1 day ago', channels: ['email'] },
  { id: 'a3', severity: 'warn', title: 'GCP cost spike', body: 'BigQuery analysis costs +42% WoW on data-platform', rule: 'SELECT provider, service, wow_growth\nFROM cost_spike_detection WHERE wow_growth > 0.3', firing: '3 hours ago', channels: ['slack'] },
  { id: 'a4', severity: 'ok', title: 'Exchange rates OK', body: 'ECB feed recovered after 15-min outage', rule: 'SELECT * FROM extractor_health\nWHERE name = \'exchange_rates\' AND status = \'ok\'', firing: null, channels: [] },
];

const DAYS: DayData[] = Array.from({ length: 30 }, (_, i) => {
  const d = i + 1;
  const gcp = 120 + Math.random() * 80;
  const azure = 200 + Math.random() * 100;
  const llm = 80 + Math.random() * 60;
  return { day: d, label: `Nov ${d}`, gcp, azure, llm, total: gcp + azure + llm };
});

const PROJECTS = [
  { name: 'data-platform', skus: [{ sku: 'Various', mtd: 8412, delta: 42.1, prev: 5917 }] },
  { name: 'ml-inference', skus: [{ sku: 'GPT-4o + Claude', mtd: 12340, delta: 18.0, prev: 10458 }] },
];

const TAG_VOCAB: Record<string, string[]> = {
  env: ['prod', 'staging', 'dev'],
  team: ['data', 'ml', 'platform', 'devops'],
  service: ['analytics', 'billing', 'inference', 'storage'],
};

export const FINNA_DATA: AppData = {
  PROJECTS,
  COSTS,
  RUNS,
  CONNECTIONS,
  ALERTS,
  DAYS,
  FIN_PROJECTS,
  TAG_VOCAB,
};

export { RESOURCES_BY_CONN };