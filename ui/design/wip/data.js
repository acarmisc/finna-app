// Mock data matching OpenAPI schemas. All consumed via `window.FinnaData`.
// In production: replace with API client calls.
(function(){
  const PROJECTS = [
    { id:'p_01', name:'prod-platform', slug:'prod-platform', owner:'platform-eng', cost_center:'CC-1001', budget_cap:14000, mtd: 8412.05, tags:['prod','tier-1'], note:'Primary production estate. Nightly extractor running on schedule.', provider:'gcp' },
    { id:'p_02', name:'rg-analytics', slug:'rg-analytics', owner:'data-team', cost_center:'CC-1002', budget_cap:4000, mtd: 3520.41, tags:['prod','analytics'], note:'BigQuery-heavy. Watch slot reservations on Mondays.', provider:'azure' },
    { id:'p_03', name:'rg-infra', slug:'rg-infra', owner:'sre', cost_center:'CC-1003', budget_cap:2000, mtd: 842.12, tags:['prod','infra'], note:'', provider:'azure' },
    { id:'p_04', name:'staging-ml', slug:'staging-ml', owner:'ml-team', cost_center:'CC-2002', budget_cap:800, mtd: 512.08, tags:['staging','ml'], note:'', provider:'gcp' },
    { id:'p_05', name:'rg-dev', slug:'rg-dev', owner:'platform-eng', cost_center:'CC-2001', budget_cap:500, mtd: 124.00, tags:['dev'], note:'', provider:'azure' },
    { id:'p_06', name:'claude-sonnet-prod', slug:'claude-sonnet-prod', owner:'ai-team', cost_center:'CC-3001', budget_cap:600, mtd: 569.50, tags:['llm','prod'], note:'Token spend rising. Investigate context bloat.', provider:'llm' },
    { id:'p_07', name:'gpt-4o-experiments', slug:'gpt-4o-experiments', owner:'ai-team', cost_center:'CC-3002', budget_cap:200, mtd: 62.40, tags:['llm','experiments'], note:'', provider:'llm' },
    { id:'p_08', name:'rg-mgmt', slug:'rg-mgmt', owner:'sre', cost_center:'CC-1004', budget_cap:1500, mtd: 398.22, tags:['prod','mgmt'], note:'', provider:'azure' },
    { id:'p_09', name:'data-warehouse', slug:'data-warehouse', owner:'data-team', cost_center:'CC-1005', budget_cap:6000, mtd: 4211.88, tags:['prod','analytics'], note:'', provider:'gcp' },
  ];

  const CONFIGS = [
    { id:'c_01', name:'acme-prod-azure', provider:'azure', credential_type:'service_principal', created_at:'2026-01-14', last_test:'ok', last_test_at:'4m ago', tenant_id:'8f2c…a1e9', subscription_id:'d4b2…0c81' },
    { id:'c_02', name:'acme-dev-azure', provider:'azure', credential_type:'service_principal', created_at:'2026-01-20', last_test:'err', last_test_at:'1d ago', tenant_id:'8f2c…a1e9', subscription_id:'e1a0…ff32', err:'AADSTS700082: token expired' },
    { id:'c_03', name:'acme-mgmt-azure', provider:'azure', credential_type:'managed_identity', created_at:'2026-02-02', last_test:'ok', last_test_at:'4m ago', tenant_id:'8f2c…a1e9', subscription_id:'b2c3…9012' },
    { id:'c_04', name:'prod-platform-gcp', provider:'gcp', credential_type:'service_principal', created_at:'2026-01-11', last_test:'ok', last_test_at:'4m ago', project_id:'acme-prod-platform' },
    { id:'c_05', name:'staging-ml-gcp', provider:'gcp', credential_type:'service_principal', created_at:'2026-02-18', last_test:'ok', last_test_at:'4m ago', project_id:'acme-staging-ml' },
    { id:'c_06', name:'data-warehouse-gcp', provider:'gcp', credential_type:'cli', created_at:'2026-03-02', last_test:'warn', last_test_at:'12m ago', project_id:'acme-dwh', err:'Polling, no new data in 12m' },
  ];

  // Runs: generate 40 realistic rows
  const RUN_TYPES = [
    { t:'azure_cost', prov:'azure' }, { t:'gcp_billing', prov:'gcp' },
    { t:'otel_llm', prov:'llm' }, { t:'exchange_rates', prov:'ecb' },
  ];
  const STATUSES = ['completed','completed','completed','completed','completed','failed','running','started','cancelled'];
  function makeRun(i) {
    const rt = RUN_TYPES[i % RUN_TYPES.length];
    const status = i < 2 ? (i === 0 ? 'running' : 'started') : STATUSES[(i*7) % STATUSES.length];
    const rows = status === 'failed' || status === 'cancelled' ? 0 : Math.floor(200 + Math.abs(Math.sin(i*3.1))*3200);
    const id = 'r_' + (Date.now() - i*180000).toString(36).slice(-8);
    const mins = i * 3 + Math.floor(Math.abs(Math.cos(i))*4);
    const started = mins < 60 ? `${mins} min ago` : mins < 1440 ? `${Math.floor(mins/60)}h ago` : `${Math.floor(mins/1440)}d ago`;
    const dur = status === 'running' ? '—' : status === 'failed' ? `${4 + (i%7)}s` : `${Math.floor(10+Math.abs(Math.sin(i))*80)}s`;
    return {
      run_id: id, extractor_type: rt.t, provider: rt.prov, status,
      started_at: started, finished_at: status === 'running' || status === 'started' ? null : started,
      records_extracted: rows, duration: dur,
      error_message: status === 'failed' ? (i%2===0 ? 'AADSTS700082: token expired. Re-authenticate.' : 'HTTP 429: rate limit exceeded (retries exhausted after 5 attempts)') : null,
      config_id: CONFIGS[i % CONFIGS.length].id,
    };
  }
  const RUNS = Array.from({length: 40}, (_, i) => makeRun(i));

  // Cost records — by project × SKU
  const SKUS = {
    gcp: ['BigQuery · analysis','Compute Engine','Cloud Storage','Cloud SQL','Dataflow','GKE','Cloud Functions'],
    azure: ['Virtual Machines','Storage','App Service','Cosmos DB','SQL Database','Synapse','Monitor'],
    llm: ['Claude Sonnet · Input','Claude Sonnet · Output','GPT-4o · Input','GPT-4o · Output','Embeddings'],
  };
  const COSTS = [];
  PROJECTS.forEach(p => {
    const skus = SKUS[p.provider] || SKUS.azure;
    skus.slice(0, 3 + (p.id.charCodeAt(2) % 3)).forEach((sku, i) => {
      const base = p.mtd * (0.55 - i*0.12) * (0.8 + (i%3)*0.1);
      const mtd = Math.max(12, Math.round(base * 100)/100);
      const prev = Math.round(mtd * (0.7 + ((p.id.charCodeAt(3)+i) % 10)/20) * 100)/100;
      const delta = Math.round(((mtd - prev) / prev * 1000))/10;
      COSTS.push({
        id: `cr_${p.id}_${i}`,
        prov: p.provider,
        project_id: p.id,
        name: p.name,
        sku,
        mtd, prev, delta,
        tags: p.tags,
        date: '2026-04-24',
      });
    });
  });

  // Daily series — 30 days per provider
  function daily(provider, baseline, volatility) {
    const days = [];
    const today = new Date('2026-04-24');
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today); d.setDate(today.getDate() - i);
      const dow = d.getDay();
      const weekend = (dow === 0 || dow === 6) ? 0.7 : 1;
      const trend = 1 + (29-i)*0.008;
      const noise = 1 + Math.sin(i*1.7) * volatility + Math.cos(i*0.8) * volatility*0.5;
      const spike = (i === 3 && provider === 'azure') ? 1.8 : 1;
      days.push({
        date: d.toISOString().slice(0,10),
        label: d.toLocaleDateString('en-US',{month:'short',day:'numeric'}),
        value: Math.round(baseline * weekend * trend * noise * spike * 100)/100,
      });
    }
    return days;
  }
  const DAILY = {
    azure: daily('azure', 180, 0.15),
    gcp:   daily('gcp',   260, 0.12),
    llm:   daily('llm',    35, 0.25),
  };

  const TOTALS = {
    azure: { mtd: 4884.75, prev: 3440.20, delta: +42.0 },
    gcp:   { mtd: 8623.88, prev: 7120.11, delta: +21.1 },
    llm:   { mtd:  631.90, prev:  298.40, delta: +111.7 },
    total: { mtd: 14140.53, prev: 10858.71, delta: +30.2 },
  };

  const ALERTS = [
    { id:'a_01', status:'firing', severity:'critical', description:'rg-analytics over 80% of monthly budget cap. Forecast exceeds cap by Apr 28.', rule:'cost_mtd(project) > 0.8 * budget_cap', project:'rg-analytics', triggered_at:'12 min ago' },
    { id:'a_02', status:'firing', severity:'warning',  description:'LLM cost anomaly — claude-sonnet-prod +120% vs 7d average.', rule:'zscore(cost_1d, project, window=7) > 2.0', project:'claude-sonnet-prod', triggered_at:'2h ago' },
    { id:'a_03', status:'firing', severity:'warning',  description:'Azure us-east-1 egress spike detected on Apr 22.', rule:'egress_daily > 3 * p95(egress_30d)', project:'rg-analytics', triggered_at:'1d ago' },
    { id:'a_04', status:'ack',    severity:'info',     description:'GCP BigQuery slot reservations at 92% utilization (prod-platform).', rule:'slot_util_1h > 0.9', project:'prod-platform', triggered_at:'3h ago' },
    { id:'a_05', status:'resolved', severity:'warning', description:'acme-dev-azure extraction recovered after token refresh.', rule:'extractor_health.last_success < 6h', project:'rg-dev', triggered_at:'yesterday' },
    { id:'a_06', status:'resolved', severity:'critical', description:'data-warehouse monthly cap breached on Apr 19; additional budget approved.', rule:'cost_mtd(project) > budget_cap', project:'data-warehouse', triggered_at:'5d ago' },
  ];

  const ALERT_STATS = {
    by_status: { firing: 3, ack: 1, resolved: 2 },
    by_severity: { critical: 2, warning: 3, info: 1 },
  };

  window.FinnaData = { PROJECTS, CONFIGS, RUNS, COSTS, DAILY, TOTALS, ALERTS, ALERT_STATS, SKUS };
})();
