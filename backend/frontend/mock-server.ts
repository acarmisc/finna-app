/**
 * Mock API server for local frontend development
 * Starts on port 8000 and serves mock data matching the real API schema
 *
 * Usage: bun backend/frontend/mock-server.ts
 */

import { serve } from 'bun';
import type { CostRecord, Run, Connection, Alert, DayData, Project, Resource, FinProject } from '../../types';

// ─── Mock Data ───────────────────────────────────────────────────────────────

const FINNA_DATA = {
  COSTS: [
    { prov: 'gcp' as const, name: 'prod-platform', sku: 'BigQuery · analysis', mtd: 4120.02, delta: 18.4, prev: 3480 },
    { prov: 'gcp' as const, name: 'prod-platform', sku: 'Compute Engine', mtd: 812.40, delta: 4.1, prev: 780 },
    { prov: 'gcp' as const, name: 'prod-platform', sku: 'Cloud Storage', mtd: 214.08, delta: -2.2, prev: 219 },
    { prov: 'gcp' as const, name: 'staging-ml', sku: 'Compute Engine', mtd: 412.08, delta: 8.2, prev: 380 },
    { prov: 'gcp' as const, name: 'staging-ml', sku: 'Vertex AI · endpoints', mtd: 188.40, delta: 32.0, prev: 142 },
    { prov: 'azure' as const, name: 'rg-analytics', sku: 'Virtual Machines', mtd: 2880.41, delta: 64.2, prev: 1754 },
    { prov: 'azure' as const, name: 'rg-analytics', sku: 'Synapse Analytics', mtd: 1214.00, delta: 11.2, prev: 1091 },
    { prov: 'azure' as const, name: 'rg-infra', sku: 'Storage', mtd: 842.12, delta: -4.1, prev: 878 },
    { prov: 'azure' as const, name: 'rg-infra', sku: 'Log Analytics', mtd: 318.20, delta: 1.2, prev: 314 },
    { prov: 'azure' as const, name: 'rg-dev', sku: 'App Service', mtd: 124.00, delta: -3.4, prev: 128 },
    { prov: 'azure' as const, name: 'rg-dev', sku: 'PostgreSQL flex', mtd: 84.00, delta: 0.0, prev: 84 },
    { prov: 'llm' as const, name: 'claude-sonnet-4', sku: 'Input tokens', mtd: 381.22, delta: 120.0, prev: 173 },
    { prov: 'llm' as const, name: 'claude-sonnet-4', sku: 'Output tokens', mtd: 188.28, delta: 96.4, prev: 96 },
    { prov: 'llm' as const, name: 'gpt-4o-mini', sku: 'Input tokens', mtd: 44.10, delta: 18.0, prev: 37 },
    { prov: 'llm' as const, name: 'gpt-4o-mini', sku: 'Output tokens', mtd: 18.30, delta: 22.0, prev: 15 },
  ] as CostRecord[],

  RUNS: [
    { id: 'r_01jf2kn8b3', type: 'azure_cost', prov: 'azure', status: 'success' as const, started: '4 min ago', dur: '42s', rows: 1204 },
    { id: 'r_01jf2kn7a1', type: 'gcp_billing', prov: 'gcp', status: 'success' as const, started: '4 min ago', dur: '1m 08s', rows: 3092 },
    { id: 'r_01jf2kn6x9', type: 'exchange_rates', prov: 'ecb', status: 'success' as const, started: '4 min ago', dur: '2s', rows: 31 },
    { id: 'r_01jf2kn5v4', type: 'otel_llm', prov: 'llm', status: 'running' as const, started: '1 min ago', dur: '—', rows: 0 },
    { id: 'r_01jf1zna2b', type: 'azure_cost', prov: 'azure', status: 'failed' as const, started: '1 day ago', dur: '5s', rows: 0, err: 'AADSTS700082: token expired' },
  ] as Run[],

  CONNECTIONS: [
    { id: 'c_az_prod', prov: 'azure', name: 'acme-prod', scope: 'Subscription · Cost Management Reader', status: 'ok' as const, lastRun: '4m ago', rows: '1,204', auth: 'service_principal', expires: 'in 42 days', projectId: 'p_platform', resources: [] },
    { id: 'c_gcp_prod', prov: 'gcp', name: 'prod-platform', scope: 'BQ billing export · dataset: billing', status: 'ok' as const, lastRun: '4m ago', rows: '3,092', auth: 'adc', expires: 'n/a', projectId: 'p_platform', resources: [] },
    { id: 'c_gcp_ml', prov: 'gcp', name: 'staging-ml', scope: 'BQ billing export · dataset: billing_ml', status: 'ok' as const, lastRun: '4m ago', rows: '208', auth: 'service_account_key', expires: 'in 184 days', projectId: 'p_ml', resources: [] },
    { id: 'c_llm_us', prov: 'llm', name: 'otel-gateway-us', scope: 'OTel collector · 0.0.0.0:4317', status: 'warn' as const, lastRun: '12m ago', auth: 'otlp', expires: 'n/a', projectId: 'p_ml', resources: [] },
  ] as Connection[],

  ALERTS: [
    { id: 'a1', severity: 'err' as const, title: 'rg-analytics over budget', body: '$8,200 of $10,000 used. Forecast exceeds cap by Nov 28.', rule: "cost_mtd('rg-analytics') > 0.8 * budget", firing: '12m ago', channels: ['#finops · Slack', 'oncall@acme.co'] },
    { id: 'a2', severity: 'warn' as const, title: 'LLM cost anomaly — claude-sonnet-4', body: '+120% vs 7d average. 3 traces flagged for review.', rule: "zscore(cost_1d, 'claude-sonnet-4', window=7) > 2.0", firing: '2h ago', channels: ['#finops · Slack'] },
    { id: 'a3', severity: 'ok' as const, title: 'Nightly extraction SLA', body: 'All 4 extractors completed within 15 min window.', rule: 'extractor_health.last_success < 6h', firing: null, channels: ['oncall@acme.co'] },
    { id: 'a5', severity: 'warn' as const, title: 'BigQuery scan cost spike — prod-platform', body: '$412 in the last 6 hours across 18 queries.', rule: "sum(cost_1h, 'prod-platform', sku='BigQuery') > 60 for 3h", firing: '42m ago', channels: ['#finops · Slack'] },
  ] as Alert[],

  DAYS: Array.from({ length: 30 }, (_, i) => {
    const day = i + 1;
    const seasonal = Math.sin((i - 2) * 0.55);
    const gcp = Math.round(260 + seasonal * 70 + i * 4);
    const azure = Math.round(170 + Math.cos(i * 0.4) * 50 + i * 3);
    const llm = Math.round(18 + i * 1.6 + Math.max(0, i - 20) * 8);
    return { day, label: `Nov ${day}`, gcp, azure, llm, total: gcp + azure + llm };
  }) as DayData[],

  FIN_PROJECTS: [
    { id: 'p_platform', name: 'Platform', slug: 'platform', owner: 'platform-eng@acme.co', costCenter: 'eng-001', budgetCap: 14000, mtd: 8412.22, tags: { env: 'prod', business_unit: 'core' }, created: '2025-02-14', note: 'Core platform + shared data infra.' },
    { id: 'p_ml', name: 'ML & AI', slug: 'ml-ai', owner: 'ml-team@acme.co', costCenter: 'ml-002', budgetCap: 3500, mtd: 1241.40, tags: { env: 'mixed', business_unit: 'ai' }, created: '2025-04-02', note: 'Training, serving and LLM spend.' },
    { id: 'p_analytics', name: 'Analytics', slug: 'analytics', owner: 'data@acme.co', costCenter: 'data-004', budgetCap: 10000, mtd: 4094.41, tags: { env: 'prod', business_unit: 'data' }, created: '2024-11-06', note: 'BI, dashboards, warehouse.' },
    { id: 'p_dev', name: 'Dev & Staging', slug: 'dev', owner: 'devops@acme.co', costCenter: 'eng-002', budgetCap: 900, mtd: 208.00, tags: { env: 'dev', business_unit: 'core' }, created: '2025-01-20', note: 'Developer sandboxes and CI.' },
  ] as FinProject[],
};

// ─── Auth ────────────────────────────────────────────────────────────────────

const VALID_USERS = [
  { username: 'admin', password: 'admin', role: 'admin' },
  { username: 'user', password: 'password', role: 'user' },
];

function generateToken(username: string): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ sub: username, iat: Date.now(), exp: Date.now() + 3600000 })).toString('base64url');
  const signature = Buffer.from('mock-signature-12345').toString('base64url');
  return `${header}.${payload}.${signature}`;
}

function verifyAuth(url: URL, req: Request): string | null {
  if (url.pathname === '/healthz' || url.pathname === '/api/v1/auth/token') return null;
  if (url.pathname.startsWith('/api/v1/auth/')) return null;

  const auth = req.headers.get('Authorization');
  if (auth?.startsWith('Bearer ')) {
    return auth.slice(7);
  }
  return null;
}

// ─── Server ──────────────────────────────────────────────────────────────────

export default serve({
  port: 8000,
  fetch(req, server) {
    const url = new URL(req.url);
    const method = req.method;

    // Skip auth for dev: if no token and it's a frontend request, allow it
    const token = verifyAuth(url, req);
    const hasToken = token !== null;

    // Auth endpoint
    if (method === 'POST' && url.pathname === '/api/v1/auth/token') {
      return handleLogin(req);
    }

    // Health check
    if (method === 'GET' && url.pathname === '/healthz') {
      return json({ status: 'ok', api: 'finops-mock', database: 'mock' });
    }

    // Require auth
    if (!hasToken) {
      return json({ error: 'unauthorized', message: 'Missing token' }, 401);
    }

    // Costs
    if (method === 'GET' && url.pathname === '/api/v1/costs') {
      const costs = FINNA_DATA.COSTS.map((c, i) => ({ ...c, id: `cost_${i}`, date: '2025-11-14', currency: 'USD', tags: {} }));
      return json({
        costs,
        totals: {
          gcp: FINNA_DATA.DAYS.reduce((a, d) => a + d.gcp, 0),
          azure: FINNA_DATA.DAYS.reduce((a, d) => a + d.azure, 0),
          llm: FINNA_DATA.DAYS.reduce((a, d) => a + d.llm, 0),
        },
        filtered: true,
        startDate: '2025-11-01',
        endDate: '2025-11-14',
      });
    }

    if (method === 'GET' && url.pathname === '/api/v1/costs/totals') {
      return json({
        totals: {
          gcp: { total: FINNA_DATA.DAYS.reduce((a, d) => a + d.gcp, 0), records: FINNA_DATA.DAYS.length },
          azure: { total: FINNA_DATA.DAYS.reduce((a, d) => a + d.azure, 0), records: FINNA_DATA.DAYS.length },
          llm: { total: FINNA_DATA.DAYS.reduce((a, d) => a + d.llm, 0), records: FINNA_DATA.DAYS.length },
        },
        startDate: '2025-11-01',
        endDate: '2025-11-14',
      });
    }

    if (method === 'GET' && url.pathname === '/api/v1/costs/by-sku') {
      return json({ costs: FINNA_DATA.COSTS, totalRows: FINNA_DATA.COSTS.length });
    }

    if (method === 'GET' && url.pathname === '/api/v1/costs/daily') {
      const dailyData = FINNA_DATA.DAYS.flatMap(d => [
        { date: d.label, gcp: d.gcp, azure: 0, llm: 0 },
        { date: d.label, gcp: 0, azure: d.azure, llm: 0 },
        { date: d.label, gcp: 0, azure: 0, llm: d.llm },
      ]);
      return json({ days: dailyData, startDate: '2025-11-01', endDate: '2025-11-14' });
    }

    // Config/Connections
    if (method === 'GET' && url.pathname === '/api/v1/config') {
      return json(FINNA_DATA.CONNECTIONS.map(c => ({
        id: c.id, provider: c.prov, name: c.name,
        credential_type: c.auth.replace(/\s+/g, '_') as any,
        config: {}, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      })));
    }

    if (method === 'POST' && url.pathname === '/api/v1/config') {
      return json({
        id: `c_mock_${Date.now()}`, provider: 'azure', name: 'New Connection',
        credential_type: 'service_principal', config: {},
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      }, 201);
    }

    if (method === 'DELETE' && url.pathname.match(/^\/api\/v1\/config\/.+$/)) {
      return new Response(null, { status: 204 });
    }

    // Alerts
    if (method === 'GET' && url.pathname === '/api/v1/alerts') {
      return json({ alerts: FINNA_DATA.ALERTS, count: FINNA_DATA.ALERTS.length });
    }

    if (method === 'GET' && url.pathname === '/api/v1/alerts/active') {
      const active = FINNA_DATA.ALERTS.filter(a => a.severity !== 'ok');
      return json({ alerts: active, count: active.length });
    }

    if (method === 'GET' && url.pathname === '/api/v1/alerts/stats') {
      return json({ stats: [] });
    }

    // Extractors/Runs
    if (method === 'GET' && url.pathname === '/api/v1/extractors/status') {
      return json({ runs: FINNA_DATA.RUNS, count: FINNA_DATA.RUNS.length });
    }

    if (method === 'POST' && url.pathname === '/api/v1/extractors/run') {
      return json({ run_id: `r_mock_${Date.now()}`, status: 'started' });
    }

    // Projects
    if (method === 'GET' && url.pathname === '/api/v1/config/projects') {
      return json(FINNA_DATA.FIN_PROJECTS);
    }

    // 404
    return json({ error: 'not_found', message: `${method} ${url.pathname}` }, 404);
  },
});

function json(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  });
}

function handleLogin(req: Request): Response {
  return req.text().then(async (body) => {
    try {
      const { username, password } = JSON.parse(body);
      const user = VALID_USERS.find(u => u.username === username && u.password === password);
      if (!user) return json({ error: 'authentication_failed', message: 'Invalid credentials' }, 401);
      return json({ token: generateToken(username) });
    } catch {
      return json({ error: 'invalid_request', message: 'Invalid JSON' }, 400);
    }
  });
}

console.log('🚀 Mock FinOps API server → http://localhost:8000');
console.log('🔑 Credentials: admin/admin');
