import type { CostRecord, Run, Connection, Alert, DayData, FinProject, Resource } from '../types';

const FIN_PROJECTS: FinProject[] = [
  { id: 'p_platform', name: 'Platform', slug: 'platform', owner: 'platform-eng@acme.co',
    costCenter: 'eng-001', budgetCap: 14000, mtd: 8412.22,
    tags: { env: 'prod', business_unit: 'core' },
    created: '2025-02-14', note: 'Core platform + shared data infra.' },
  { id: 'p_ml', name: 'ML & AI', slug: 'ml-ai', owner: 'ml-team@acme.co',
    costCenter: 'ml-002', budgetCap: 3500, mtd: 1241.40,
    tags: { env: 'mixed', business_unit: 'ai' },
    created: '2025-04-02', note: 'Training, serving and LLM spend.' },
  { id: 'p_analytics', name: 'Analytics', slug: 'analytics', owner: 'data@acme.co',
    costCenter: 'data-004', budgetCap: 10000, mtd: 4094.41,
    tags: { env: 'prod', business_unit: 'data' },
    created: '2024-11-06', note: 'BI, dashboards, warehouse.' },
  { id: 'p_dev', name: 'Dev & Staging', slug: 'dev', owner: 'devops@acme.co',
    costCenter: 'eng-002', budgetCap: 900, mtd: 208.00,
    tags: { env: 'dev', business_unit: 'core' },
    created: '2025-01-20', note: 'Developer sandboxes and CI.' },
];

const RESOURCES_BY_CONN: Record<string, Resource[]> = {
  c_az_prod: [
    { id: 'r_vm01', name: 'vm-api-prod-01', type: 'Virtual Machine', native: '/subscriptions/acme-prod/resourceGroups/rg-api/providers/Microsoft.Compute/virtualMachines/vm-api-prod-01', mtd: 1284.20, tags: { env: 'prod', team: 'platform', cost_center: 'eng-001' } },
    { id: 'r_vm02', name: 'vm-api-prod-02', type: 'Virtual Machine', native: '/subscriptions/acme-prod/.../vm-api-prod-02', mtd: 1211.88, tags: { env: 'prod', team: 'platform' } },
    { id: 'r_syn01', name: 'syn-warehouse', type: 'Synapse Pool', native: '/subscriptions/acme-prod/.../synapseWorkspaces/syn-warehouse', mtd: 1214.00, tags: { env: 'prod', team: 'data' } },
    { id: 'r_sto01', name: 'acmeprodsa01', type: 'Storage Account', native: '/subscriptions/acme-prod/.../storageAccounts/acmeprodsa01', mtd: 442.12, tags: { env: 'prod' } },
    { id: 'r_log01', name: 'log-analytics-01', type: 'Log Workspace', native: '/subscriptions/acme-prod/.../workspaces/log-analytics-01', mtd: 318.20, tags: { env: 'prod' } },
  ],
  c_az_mgmt: [
    { id: 'r_sto02', name: 'acmemgmtsa', type: 'Storage Account', native: '/subscriptions/acme-mgmt/.../acmemgmtsa', mtd: 400.00, tags: { env: 'prod' } },
  ],
  c_az_dev: [
    { id: 'r_app01', name: 'app-dev-web', type: 'App Service', native: '/subscriptions/acme-dev/.../app-dev-web', mtd: 124.00, tags: { env: 'dev' } },
    { id: 'r_pg01', name: 'pg-dev-flex', type: 'PostgreSQL', native: '/subscriptions/acme-dev/.../pg-dev-flex', mtd: 84.00, tags: { env: 'dev' } },
  ],
  c_gcp_prod: [
    { id: 'r_bq01', name: 'billing', type: 'BQ Dataset', native: 'prod-platform:billing', mtd: 4120.02, tags: { env: 'prod', team: 'finops' } },
    { id: 'r_gce01', name: 'gke-prod-nodepool', type: 'Compute Engine', native: 'prod-platform/gke-prod-nodepool', mtd: 812.40, tags: { env: 'prod', team: 'platform' } },
    { id: 'r_gcs01', name: 'acme-prod-logs', type: 'Cloud Storage', native: 'gs://acme-prod-logs', mtd: 214.08, tags: { env: 'prod' } },
  ],
  c_gcp_ml: [
    { id: 'r_gce02', name: 'training-pool', type: 'Compute Engine', native: 'staging-ml/training-pool', mtd: 412.08, tags: { env: 'staging', team: 'ml' } },
    { id: 'r_vtx01', name: 'endpoint-sonnet', type: 'Vertex Endpoint', native: 'staging-ml/endpoints/endpoint-sonnet', mtd: 188.40, tags: { env: 'staging', team: 'ml' } },
  ],
  c_llm_us: [
    { id: 'r_llm01', name: 'claude-sonnet-4', type: 'LLM Model', native: 'otlp://otel-gateway-us/claude-sonnet-4', mtd: 569.50, tags: { team: 'ml' } },
    { id: 'r_llm02', name: 'gpt-4o-mini', type: 'LLM Model', native: 'otlp://otel-gateway-us/gpt-4o-mini', mtd: 62.40, tags: { team: 'ml' } },
  ],
  c_llm_eu: [
    { id: 'r_llm03', name: 'claude-haiku', type: 'LLM Model', native: 'otlp://otel-gateway-eu/claude-haiku', mtd: 88.20, tags: { team: 'ml', region: 'eu' } },
  ],
};

const PROJECT_BINDINGS: Record<string, string | null> = {
  c_az_prod: 'p_platform',
  c_az_mgmt: 'p_platform',
  c_gcp_prod: 'p_platform',
  c_az_dev: 'p_dev',
  c_gcp_ml: 'p_ml',
  c_llm_us: 'p_ml',
  c_llm_eu: null,
};

const CONNECTIONS: Connection[] = [
  { id: 'c_az_prod', prov: 'azure', name: 'acme-prod', scope: 'Subscription · Cost Management Reader', status: 'ok', lastRun: '4m ago', rows: '1,204', auth: 'service principal', expires: 'in 42 days' },
  { id: 'c_az_dev', prov: 'azure', name: 'acme-dev', scope: 'Subscription · Cost Management Reader', status: 'err', lastRun: '1d ago', err: 'AADSTS700082 · token expired', auth: 'device code', expires: 'expired' },
  { id: 'c_az_mgmt', prov: 'azure', name: 'acme-mgmt', scope: 'RG: rg-analytics, rg-infra', status: 'ok', lastRun: '4m ago', rows: '412', auth: 'service principal', expires: 'in 68 days' },
  { id: 'c_gcp_prod', prov: 'gcp', name: 'prod-platform', scope: 'BQ billing export · dataset: billing', status: 'ok', lastRun: '4m ago', rows: '3,092', auth: 'ADC (gcloud)', expires: 'n/a' },
  { id: 'c_gcp_ml', prov: 'gcp', name: 'staging-ml', scope: 'BQ billing export · dataset: billing_ml', status: 'ok', lastRun: '4m ago', rows: '208', auth: 'service account key', expires: 'in 184 days' },
  { id: 'c_llm_us', prov: 'llm', name: 'otel-gateway-us', scope: 'OTel collector · 0.0.0.0:4317', status: 'warn', lastRun: '12m ago', note: 'polling · no new spans in 10m', auth: 'OTLP', expires: 'n/a' },
  { id: 'c_llm_eu', prov: 'llm', name: 'otel-gateway-eu', scope: 'OTel collector · 0.0.0.0:4317', status: 'ok', lastRun: '4m ago', rows: '87', auth: 'OTLP', expires: 'n/a' },
].map(c => ({
  ...c,
  projectId: PROJECT_BINDINGS[c.id] ?? null,
  resources: RESOURCES_BY_CONN[c.id] || [],
}));

const rawProjects = [
  { prov: 'gcp' as const, name: 'prod-platform', skus: [
    { sku: 'BigQuery · analysis', mtd: 4120.02, delta: 18.4, prev: 3480 },
    { sku: 'Compute Engine', mtd: 812.40, delta: 4.1, prev: 780 },
    { sku: 'Cloud Storage', mtd: 214.08, delta: -2.2, prev: 219 },
  ]},
  { prov: 'gcp' as const, name: 'staging-ml', skus: [
    { sku: 'Compute Engine', mtd: 412.08, delta: 8.2, prev: 380 },
    { sku: 'Vertex AI · endpoints', mtd: 188.40, delta: 32.0, prev: 142 },
  ]},
  { prov: 'azure' as const, name: 'rg-analytics', skus: [
    { sku: 'Virtual Machines', mtd: 2880.41, delta: 64.2, prev: 1754 },
    { sku: 'Synapse Analytics', mtd: 1214.00, delta: 11.2, prev: 1091 },
  ]},
  { prov: 'azure' as const, name: 'rg-infra', skus: [
    { sku: 'Storage', mtd: 842.12, delta: -4.1, prev: 878 },
    { sku: 'Log Analytics', mtd: 318.20, delta: 1.2, prev: 314 },
  ]},
  { prov: 'azure' as const, name: 'rg-dev', skus: [
    { sku: 'App Service', mtd: 124.00, delta: -3.4, prev: 128 },
    { sku: 'PostgreSQL flex', mtd: 84.00, delta: 0.0, prev: 84 },
  ]},
  { prov: 'llm' as const, name: 'claude-sonnet-4', skus: [
    { sku: 'Input tokens', mtd: 381.22, delta: 120.0, prev: 173 },
    { sku: 'Output tokens', mtd: 188.28, delta: 96.4, prev: 96 },
  ]},
  { prov: 'llm' as const, name: 'gpt-4o-mini', skus: [
    { sku: 'Input tokens', mtd: 44.10, delta: 18.0, prev: 37 },
    { sku: 'Output tokens', mtd: 18.30, delta: 22.0, prev: 15 },
  ]},
];

const COSTS: CostRecord[] = rawProjects.flatMap(p =>
  p.skus.map(s => ({ prov: p.prov, name: p.name, sku: s.sku, mtd: s.mtd, delta: s.delta, prev: s.prev }))
);

const RUNS: Run[] = [
  { id: 'r_01jf2kn8b3', type: 'azure_cost', prov: 'azure', status: 'success', started: '4 min ago', dur: '42s', rows: 1204 },
  { id: 'r_01jf2kn7a1', type: 'gcp_billing', prov: 'gcp', status: 'success', started: '4 min ago', dur: '1m 08s', rows: 3092 },
  { id: 'r_01jf2kn6x9', type: 'exchange_rates', prov: 'ecb', status: 'success', started: '4 min ago', dur: '2s', rows: 31 },
  { id: 'r_01jf2kn5v4', type: 'otel_llm', prov: 'llm', status: 'running', started: '1 min ago', dur: '—', rows: 0 },
  { id: 'r_01jf1zna2b', type: 'azure_cost', prov: 'azure', status: 'failed', started: '1 day ago', dur: '5s', rows: 0, err: 'AADSTS700082: token expired (acme-dev)' },
  { id: 'r_01jf1wmc84', type: 'gcp_billing', prov: 'gcp', status: 'success', started: '1 day ago', dur: '1m 12s', rows: 3140 },
  { id: 'r_01jf1wmb78', type: 'azure_cost', prov: 'azure', status: 'success', started: '1 day ago', dur: '39s', rows: 1188 },
  { id: 'r_01jf1wma22', type: 'exchange_rates', prov: 'ecb', status: 'success', started: '1 day ago', dur: '2s', rows: 31 },
  { id: 'r_01jf1r28kk', type: 'otel_llm', prov: 'llm', status: 'success', started: '1 day ago', dur: '8s', rows: 842 },
  { id: 'r_01jf1kn812', type: 'gcp_billing', prov: 'gcp', status: 'success', started: '2 days ago', dur: '1m 04s', rows: 3081 },
  { id: 'r_01jf1kn7hx', type: 'azure_cost', prov: 'azure', status: 'success', started: '2 days ago', dur: '44s', rows: 1192 },
  { id: 'r_01jf0n2p1k', type: 'otel_llm', prov: 'llm', status: 'failed', started: '3 days ago', dur: '18s', rows: 0, err: 'connection refused: otel-gateway-eu:4317' },
];

const ALERTS: Alert[] = [
  { id: 'a1', severity: 'err', title: 'rg-analytics over budget',
    body: '$8,200 of $10,000 used. Forecast exceeds cap by Nov 28.',
    rule: "cost_mtd('rg-analytics') > 0.8 * budget",
    firing: '12m ago', channels: ['#finops · Slack', 'oncall@acme.co'] },
  { id: 'a2', severity: 'warn', title: 'LLM cost anomaly — claude-sonnet-4',
    body: '+120% vs 7d average. 3 traces flagged for review.',
    rule: "zscore(cost_1d, 'claude-sonnet-4', window=7) > 2.0",
    firing: '2h ago', channels: ['#finops · Slack'] },
  { id: 'a3', severity: 'ok', title: 'Nightly extraction SLA',
    body: 'All 4 extractors completed within 15 min window.',
    rule: 'extractor_health.last_success < 6h',
    firing: null, channels: ['oncall@acme.co'] },
  { id: 'a4', severity: 'ok', title: 'Exchange rates freshness',
    body: 'ECB rates updated at 16:05 UTC · within 24h threshold.',
    rule: 'max(exchange_rates.fetched_at) < 24h',
    firing: null, channels: ['#finops · Slack'] },
  { id: 'a5', severity: 'warn', title: 'BigQuery scan cost spike — prod-platform',
    body: '$412 in the last 6 hours across 18 queries. Dashboard auto-refresh suspected.',
    rule: "sum(cost_1h, 'prod-platform', sku='BigQuery') > 60 for 3h",
    firing: '42m ago', channels: ['#finops · Slack'] },
];

const DAYS: DayData[] = Array.from({ length: 30 }, (_, i) => {
  const day = i + 1;
  const seasonal = Math.sin((i - 2) * 0.55);
  const spike = i === 18 ? 180 : 0;
  const gcp = Math.round(260 + seasonal * 70 + i * 4);
  const azure = Math.round(170 + Math.cos(i * 0.4) * 50 + i * 3 + spike);
  const llm = Math.round(18 + i * 1.6 + Math.max(0, i - 20) * 8);
  return { day, label: `Nov ${day}`, gcp, azure, llm, total: gcp + azure + llm };
});

export const TAG_VOCAB: Record<string, string[]> = {
  env: ['prod', 'staging', 'dev', 'sandbox'],
  team: ['platform', 'data', 'ml', 'finops', 'sre'],
  cost_center: ['eng-001', 'eng-002', 'ml-002', 'data-004'],
  region: ['us', 'eu', 'apac'],
  business_unit: ['core', 'ai', 'data', 'sales'],
};

export const FINNA_DATA = {
  PROJECTS: rawProjects,
  COSTS,
  RUNS,
  CONNECTIONS,
  ALERTS,
  DAYS,
  FIN_PROJECTS,
  TAG_VOCAB,
};
