// Pages part 1: Login, Dashboard, Projects, Cost Explorer
const { useState: uS, useEffect: uE, useMemo: uM } = React;

// ---------- LOGIN ----------
const SSO_PROVIDERS = [
  { id:'google',    name:'Continue with Google',     meta:'OAuth',
    svg:(<svg viewBox="0 0 18 18" width="18" height="18"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.79 2.71v2.26h2.9c1.7-1.56 2.69-3.87 2.69-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.9-2.26c-.81.54-1.84.86-3.06.86-2.36 0-4.36-1.59-5.07-3.74H.96v2.34A8.99 8.99 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.93 10.68A5.4 5.4 0 0 1 3.64 9c0-.58.1-1.15.29-1.68V4.98H.96A8.99 8.99 0 0 0 0 9c0 1.45.35 2.83.96 4.02l2.97-2.34z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58A8.99 8.99 0 0 0 9 0 9 9 0 0 0 .96 4.98L3.93 7.32C4.64 5.17 6.64 3.58 9 3.58z"/></svg>) },
  { id:'microsoft', name:'Continue with Microsoft',  meta:'OAuth',
    svg:(<svg viewBox="0 0 18 18" width="18" height="18"><rect x="1" y="1" width="7.5" height="7.5" fill="#F25022"/><rect x="9.5" y="1" width="7.5" height="7.5" fill="#7FBA00"/><rect x="1" y="9.5" width="7.5" height="7.5" fill="#00A4EF"/><rect x="9.5" y="9.5" width="7.5" height="7.5" fill="#FFB900"/></svg>) },
  { id:'okta',      name:'Continue with Okta',       meta:'SAML',
    svg:(<svg viewBox="0 0 18 18" width="18" height="18"><circle cx="9" cy="9" r="7" fill="none" stroke="currentColor" strokeWidth="3"/></svg>) },
  { id:'github',    name:'Continue with GitHub',     meta:'OAuth',
    svg:(<svg viewBox="0 0 18 18" width="18" height="18" fill="currentColor"><path d="M9 .5a8.5 8.5 0 0 0-2.69 16.57c.43.08.59-.18.59-.41 0-.2-.01-.74-.01-1.45-2.4.52-2.9-1.16-2.9-1.16-.4-1-.97-1.27-.97-1.27-.79-.54.06-.53.06-.53.87.06 1.33.9 1.33.9.78 1.33 2.04.95 2.54.72.08-.56.3-.95.55-1.17-1.92-.22-3.94-.96-3.94-4.27 0-.94.34-1.71.89-2.31-.09-.22-.39-1.1.08-2.29 0 0 .72-.23 2.36.88a8.2 8.2 0 0 1 4.3 0c1.64-1.11 2.36-.88 2.36-.88.47 1.19.17 2.07.08 2.29.55.6.89 1.37.89 2.31 0 3.32-2.02 4.05-3.95 4.26.31.27.59.8.59 1.62 0 1.17-.01 2.11-.01 2.4 0 .23.16.5.6.41A8.5 8.5 0 0 0 9 .5z"/></svg>) },
];

function LoginPage({ onAuth }) {
  const [showEmail, setShowEmail] = uS(false);
  const [user, setUser] = uS('finops@acme.co');
  const [pw, setPw] = uS('');
  const [err, setErr] = uS('');
  const [loadingId, setLoadingId] = uS(null);

  const submit = (e) => {
    e.preventDefault();
    setErr('');
    if (!pw) { setErr('Enter a password to continue'); return; }
    setLoadingId('email');
    setTimeout(() => { setLoadingId(null); onAuth(); }, 600);
  };

  const ssoLogin = (id) => {
    setLoadingId(id);
    setTimeout(() => { setLoadingId(null); onAuth(); }, 700);
  };

  return (
    <div className="login-wrap">
      <aside className="login-brand">
        <div className="login-brand-mark">
          <span className="caret">&gt;</span>
          <span>finna</span>
        </div>
        <div className="login-brand-headline">
          <h1>Cloud + LLM costs, <span className="accent">in one console.</span></h1>
          <p>Track Azure, GCP and LLM spend, set budgets per project, and catch anomalies before they hit your bill.</p>
        </div>
        <div className="login-brand-stats">
          <div className="item"><div className="v">$1.2M</div><div className="l">Tracked monthly</div></div>
          <div className="item"><div className="v">3</div><div className="l">Cloud + LLM</div></div>
          <div className="item"><div className="v">99.9%</div><div className="l">Extractor uptime</div></div>
        </div>
      </aside>

      <div className="login-pane">
        <div className="login-card">
          <h2 className="title">Sign in to Finna</h2>
          <p className="subtitle">Use your work account to access the FinOps console.</p>

          <div className="sso-list">
            {SSO_PROVIDERS.map(p => (
              <button key={p.id} className="sso-btn" onClick={()=>ssoLogin(p.id)} disabled={!!loadingId}>
                <span className="ico" style={{color: p.id==='okta' ? '#007DC1' : 'var(--fg)'}}>{p.svg}</span>
                <span className="name">{loadingId===p.id ? 'Redirecting…' : p.name}</span>
                <span className="meta">{p.meta}</span>
              </button>
            ))}
            <button className="sso-btn" onClick={()=>ssoLogin('saml')} disabled={!!loadingId}>
              <span className="ico"><Icon name="key-round" size={16}/></span>
              <span className="name">{loadingId==='saml' ? 'Redirecting…' : 'SAML SSO'}</span>
              <span className="meta">Enterprise</span>
            </button>
          </div>

          <div className="login-divider"><span>or</span></div>

          {!showEmail ? (
            <button className="login-email-toggle" onClick={()=>setShowEmail(true)}>
              Sign in with email and password
            </button>
          ) : (
            <form className="login-email-form" onSubmit={submit}>
              <div className="field">
                <div className="label">Email</div>
                <input className={`inp ${err?'error':''}`} value={user} onChange={e=>setUser(e.target.value)} placeholder="you@company.com" autoFocus/>
              </div>
              <div className="field">
                <div className="row" style={{marginBottom:6}}>
                  <span className="label" style={{margin:0}}>Password</span>
                  <a href="#" onClick={e=>e.preventDefault()}>Forgot?</a>
                </div>
                <input type="password" className={`inp ${err?'error':''}`} value={pw} onChange={e=>setPw(e.target.value)} placeholder="••••••••"/>
                {err && <div className="hint error" style={{marginTop:6}}>{err}</div>}
              </div>
              <Button variant="primary" type="submit" bracket block disabled={loadingId==='email'}>
                {loadingId==='email' ? 'Authenticating…' : 'Sign in'}
              </Button>
              <button type="button" className="login-email-toggle" onClick={()=>setShowEmail(false)} style={{marginTop:0}}>← Back to SSO options</button>
            </form>
          )}

          <div className="login-foot">
            <span>Need an account? <a href="#" onClick={e=>e.preventDefault()} style={{color:'var(--primary)', textDecoration:'none'}}>Contact admin</a></span>
            <span className="mono">v2.4.1</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- DASHBOARD ----------
// ---------- DASHBOARD ----------
const DEFAULT_KPIS = ['total','azure','gcp','llm','alerts'];

function DashboardPage({ range = 'mtd' }) {
  const D = window.FinnaData;
  const scale = { mtd: 1, '7d': 0.23, '30d': 1.05, '90d': 3.08 }[range] || 1;
  const rangeLabel = { mtd:'MTD', '7d':'last 7 days', '30d':'last 30 days', '90d':'last 90 days' }[range];
  const rangeDelta = { mtd:'vs last month', '7d':'vs prev 7d', '30d':'vs prev 30d', '90d':'vs prev 90d' }[range];
  const totals = D.TOTALS;
  const daily = D.DAILY;
  const topProjects = [...D.PROJECTS].sort((a,b) => b.mtd - a.mtd).slice(0, 5)
    .map(p => ({ ...p, windowed: +(p.mtd * scale).toFixed(2) }));
  const recentRuns = D.RUNS.slice(0, 10);

  const llmBreakdown = [
    { name:'Claude Sonnet', value: +(totals.llm.mtd * scale * 0.58).toFixed(2), tokens:'4.2M in · 1.8M out' },
    { name:'GPT-4o',        value: +(totals.llm.mtd * scale * 0.31).toFixed(2), tokens:'2.1M in · 0.9M out' },
    { name:'Embeddings',    value: +(totals.llm.mtd * scale * 0.08).toFixed(2), tokens:'12.4M' },
    { name:'Haiku',         value: +(totals.llm.mtd * scale * 0.03).toFixed(2), tokens:'620K in · 180K out' },
  ];
  const llmTotal = llmBreakdown.reduce((s,x)=>s+x.value, 0);

  const [kpiOrder, setKpiOrder] = uS(() => {
    try { return JSON.parse(localStorage.getItem('finna_kpi_order')) || DEFAULT_KPIS; }
    catch { return DEFAULT_KPIS; }
  });
  const [hidden, setHidden] = uS(() => {
    try { return new Set(JSON.parse(localStorage.getItem('finna_kpi_hidden')) || []); }
    catch { return new Set(); }
  });
  const [editMode, setEditMode] = uS(false);
  const dragRef = React.useRef(null);

  const persistOrder = (next) => { setKpiOrder(next); localStorage.setItem('finna_kpi_order', JSON.stringify(next)); };
  const toggleHidden = (id) => {
    const next = new Set(hidden);
    next.has(id) ? next.delete(id) : next.add(id);
    setHidden(next);
    localStorage.setItem('finna_kpi_hidden', JSON.stringify([...next]));
  };

  const kpiDefs = {
    total: { label:`Total ${rangeLabel}`, value: money(totals.total.mtd * scale), unit:'USD', delta:`+${(totals.total.delta*scale).toFixed(1)}%`, deltaDir:'up', meta:rangeDelta, accent:'primary' },
    azure: { label:`Azure ${rangeLabel}`, value: money(totals.azure.mtd * scale), unit:'USD', delta:`+${totals.azure.delta}%`, deltaDir:'up', meta:'3 subscriptions', accent:'azure' },
    gcp:   { label:`GCP ${rangeLabel}`,   value: money(totals.gcp.mtd * scale),   unit:'USD', delta:`+${totals.gcp.delta}%`,   deltaDir:'up', meta:'2 projects', accent:'gcp' },
    llm:   { label:`LLM ${rangeLabel}`,   value: money(totals.llm.mtd * scale),   unit:'USD', delta:`+${totals.llm.delta}%`,   deltaDir:'up', meta:'3 models', accent:'llm' },
    alerts:{ label:'Active alerts', value:'3', unit:'', delta:'2 critical', deltaDir:'up', meta:'1 warning', accent:'danger' },
  };

  const chartSeries = [
    { name:'Azure', color:'var(--azure)', data: daily.azure.map(d => ({ label:d.label, value: +(d.value * scale).toFixed(2) })) },
    { name:'GCP',   color:'var(--gcp)',   data: daily.gcp.map(d => ({ label:d.label, value: +(d.value * scale).toFixed(2) })) },
    { name:'LLM',   color:'var(--llm)',   data: daily.llm.map(d => ({ label:d.label, value: +(d.value * scale).toFixed(2) })) },
  ];

  const onDragStart = (id) => (e) => { dragRef.current = id; e.dataTransfer.effectAllowed = 'move'; };
  const onDragOver = (id) => (e) => { e.preventDefault(); };
  const onDrop = (id) => (e) => {
    e.preventDefault();
    const from = dragRef.current; if (!from || from === id) return;
    const next = [...kpiOrder];
    const fromIdx = next.indexOf(from);
    const toIdx = next.indexOf(id);
    next.splice(fromIdx, 1);
    next.splice(toIdx, 0, from);
    persistOrder(next);
    dragRef.current = null;
  };

  const visibleKpis = kpiOrder.filter(id => !hidden.has(id));
  const hiddenKpis = kpiOrder.filter(id => hidden.has(id));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <div className="sub">// last refresh · 4 min ago · all sources healthy · window: {rangeLabel}</div>
        </div>
        <div className="actions">
          <Button icon={editMode?'check':'layout-grid'} bracket onClick={()=>setEditMode(m=>!m)}>{editMode?'done':'customize'}</Button>
          <Button icon="refresh-ccw" bracket>refresh</Button>
          <Button icon="download" bracket>export</Button>
        </div>
      </div>

      {editMode && (
        <div style={{border:'1px dashed var(--border-strong)', background:'var(--surface-2)', padding:'10px 14px', marginBottom:12, display:'flex', alignItems:'center', gap:12, flexWrap:'wrap', fontSize:12.5}}>
          <span style={{color:'var(--fg-muted)'}}>Drag cards to reorder · click a hidden tile to restore</span>
          {hiddenKpis.length > 0 && (
            <>
              <span style={{color:'var(--fg-subtle)'}}>│</span>
              {hiddenKpis.map(id => (
                <button key={id} onClick={()=>toggleHidden(id)} style={{padding:'4px 10px', border:'1px solid var(--border)', background:'var(--surface)', color:'var(--fg)', cursor:'pointer', fontSize:11.5, fontWeight:500}}>+ {kpiDefs[id].label}</button>
              ))}
            </>
          )}
          {hiddenKpis.length === 0 && <span style={{color:'var(--fg-subtle)'}}>All KPIs visible</span>}
        </div>
      )}

      <div className="row row-4" style={visibleKpis.length === 5 ? {gridTemplateColumns:'repeat(5, 1fr)'} : undefined}>
        {visibleKpis.map(id => (
          <div
            key={id}
            draggable={editMode}
            onDragStart={onDragStart(id)}
            onDragOver={onDragOver(id)}
            onDrop={onDrop(id)}
            style={{position:'relative', cursor: editMode?'move':'default', opacity: editMode?0.95:1}}
          >
            <StatCard {...kpiDefs[id]}/>
            {editMode && (
              <button onClick={()=>toggleHidden(id)} title="Hide" style={{position:'absolute', top:6, right:6, width:22, height:22, border:'1px solid var(--border)', background:'var(--surface)', color:'var(--fg-muted)', cursor:'pointer', display:'grid', placeItems:'center', fontSize:10}}>×</button>
            )}
          </div>
        ))}
      </div>

      <div className="row row-2-6040-rev mt-3">
        <div className="card">
          <div className="card-hd">
            <h3>Daily cost · {rangeLabel}</h3>
            <div className="hstack">
              <span className="chip">USD</span>
              <span className="chip on">per-provider</span>
            </div>
          </div>
          <div className="card-bd">
            <LineChart series={chartSeries} width={760} height={260}/>
          </div>
        </div>
        <div className="card">
          <div className="card-hd">
            <h3>Top projects · {rangeLabel}</h3>
            <a href="#/projects" onClick={e=>{e.preventDefault();navigate('/projects');}}>view all →</a>
          </div>
          <div className="card-bd">
            <HBarList items={topProjects.map(p => ({ name:p.name, value:p.windowed, provider:p.provider }))}
              colorFor={(it) => it.provider==='azure'?'var(--azure)':it.provider==='gcp'?'var(--gcp)':'var(--llm)'}/>
          </div>
        </div>
      </div>

      <div className="row row-2-4060 mt-3">
        <div className="card">
          <div className="card-hd">
            <h3>LLM spend by model · {rangeLabel}</h3>
            <span className="chip">{money(llmTotal)} total</span>
          </div>
          <div className="card-bd">
            <div style={{display:'flex', flexDirection:'column', gap:10}}>
              {llmBreakdown.map(m => {
                const pct = Math.round((m.value/llmTotal)*100);
                return (
                  <div key={m.name}>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:4}}>
                      <div style={{display:'flex', alignItems:'center', gap:8}}>
                        <span style={{width:6, height:6, background:'var(--llm)'}}/>
                        <span style={{fontSize:12, color:'var(--fg)'}}>{m.name}</span>
                        <span style={{fontFamily:'JetBrains Mono, monospace', fontSize:10, color:'var(--fg-subtle)'}}>{m.tokens}</span>
                      </div>
                      <div style={{fontFamily:'JetBrains Mono, monospace', fontSize:12}}>
                        <span>{money(m.value)}</span>
                        <span style={{color:'var(--fg-subtle)', marginLeft:8}}>{pct}%</span>
                      </div>
                    </div>
                    <div style={{height:6, background:'var(--surface-2)', border:'1px solid var(--border)'}}>
                      <div style={{height:'100%', width:`${pct}%`, background:'var(--llm)'}}/>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-hd">
            <h3>Recent extractor runs</h3>
            <a href="#/extractors" onClick={e=>{e.preventDefault();navigate('/extractors');}}>run log →</a>
          </div>
          <div className="card-bd p0">
            <table className="tbl">
              <thead><tr>
                <th>Provider</th><th>Extractor</th><th>Status</th>
                <th className="num">Records</th><th className="num">Duration</th><th>Run ID</th>
              </tr></thead>
              <tbody>
                {recentRuns.map(r => (
                  <tr key={r.run_id}>
                    <td><ProviderBadge p={r.provider}/></td>
                    <td className="mono">{r.extractor_type}</td>
                    <td><StatusBadge status={r.status}/></td>
                    <td className="num mono">{r.records_extracted ? r.records_extracted.toLocaleString() : '—'}</td>
                    <td className="num mono">{r.duration}</td>
                    <td><span className="id">{r.run_id}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- PROJECTS LIST ----------
function ProjectsListPage() {
  const D = window.FinnaData;
  const [q, setQ] = uS('');
  const rows = D.PROJECTS.filter(p => !q || p.name.includes(q) || p.owner.includes(q) || p.tags.some(t => t.includes(q)));
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Projects</h1>
          <div className="sub">// {rows.length} projects · budgets aggregated monthly</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket>new project</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <div className="hstack-3" style={{flex:1}}>
            <div className="inp-group" style={{maxWidth:360, width:'100%'}}>
              <Icon name="search" size={14}/>
              <input className="inp" placeholder="filter name / owner / tag…" value={q} onChange={e=>setQ(e.target.value)}/>
            </div>
            <span className="chip">provider: <b>any</b></span>
            <span className="chip">budget: <b>all</b></span>
          </div>
          <span className="muted mono" style={{fontSize:11}}>sorted by · MTD desc</span>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>Name</th><th>Slug</th><th>Owner</th><th>Cost center</th>
              <th className="num">Budget cap</th><th className="num">MTD</th>
              <th>Budget used</th><th>Tags</th>
            </tr></thead>
            <tbody>
              {[...rows].sort((a,b)=>b.mtd-a.mtd).map(p => {
                const pct = (p.mtd/p.budget_cap)*100;
                return (
                  <tr key={p.id} className="clickable" onClick={()=>navigate(`/projects/${p.slug}`)}>
                    <td><span className="hstack"><ProviderBadge p={p.provider}/><b style={{fontWeight:500}}>{p.name}</b></span></td>
                    <td className="mono muted">{p.slug}</td>
                    <td>{p.owner}</td>
                    <td className="mono">{p.cost_center}</td>
                    <td className="num mono">{money(p.budget_cap, 0)}</td>
                    <td className="num mono">{money(p.mtd)}</td>
                    <td style={{minWidth:160}}>
                      <div className="hstack-3" style={{gap:10}}>
                        <div style={{flex:1}}><ProgressBar value={p.mtd} max={p.budget_cap}/></div>
                        <span className="mono num" style={{fontSize:11, minWidth:40, textAlign:'right', color: pct>=90?'var(--danger)':pct>=70?'var(--warning)':'var(--fg-muted)'}}>{pct.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td>{p.tags.map(t => <span key={t} className="chip" style={{marginRight:4}}>{t}</span>)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------- PROJECT DETAIL ----------
function ProjectDetailPage({ slug }) {
  const D = window.FinnaData;
  const p = D.PROJECTS.find(x => x.slug === slug);
  if (!p) {
    return <div className="page"><EmptyState icon="search-x" title="Project not found" message={`no project matches slug "${slug}"`} action={<Button onClick={()=>navigate('/projects')} bracket>back to projects</Button>}/></div>;
  }
  const pct = (p.mtd/p.budget_cap)*100;
  const projectCosts = D.COSTS.filter(c => c.project_id === p.id);
  const [note, setNote] = uS(p.note || '');
  const toast = useToast();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <a href="#/projects" onClick={e=>{e.preventDefault();navigate('/projects');}} style={{fontSize:11, fontFamily:'JetBrains Mono, monospace', color:'var(--fg-muted)'}}>← projects</a>
          <h1 style={{marginTop:6}}><span className="hstack-3"><ProviderBadge p={p.provider} size="lg"/>{p.name}</span></h1>
          <div className="hstack-3 sub" style={{marginTop:6}}>
            <span>owner · <b style={{color:'var(--fg)'}}>{p.owner}</b></span>
            <span>cost_center · <b style={{color:'var(--fg)'}}>{p.cost_center}</b></span>
            <span>slug · <b style={{color:'var(--fg)'}}>{p.slug}</b></span>
            <span>tags · {p.tags.map(t => <span key={t} className="chip" style={{marginRight:4}}>{t}</span>)}</span>
          </div>
        </div>
        <div className="actions">
          <Button icon="edit-3" bracket>edit</Button>
          <Button icon="trash-2" variant="danger" bracket>delete</Button>
        </div>
      </div>

      <div className="row row-2-6040-rev">
        <div className="card">
          <div className="card-hd"><h3>Monthly budget</h3><span className="chip">Apr 2026</span></div>
          <div className="card-bd">
            <div className="spread">
              <div>
                <div className="stat-lbl">MTD</div>
                <div className="stat-val" style={{fontSize:32}}>{money(p.mtd)}<span className="ccy">USD</span></div>
              </div>
              <div style={{textAlign:'right'}}>
                <div className="stat-lbl">cap</div>
                <div className="stat-val" style={{fontSize:20, color:'var(--fg-muted)'}}>{money(p.budget_cap,0)}</div>
              </div>
            </div>
            <div style={{marginTop:16}}>
              <ProgressBar value={p.mtd} max={p.budget_cap} stepped segments={20}/>
              <div className="hstack spread mt-2">
                <span className="mono" style={{fontSize:11, color:'var(--fg-muted)'}}>{pct.toFixed(1)}% utilized</span>
                <span className="mono" style={{fontSize:11, color: pct>=90?'var(--danger)':pct>=70?'var(--warning)':'var(--accent)'}}>
                  {pct>=90?'OVER THRESHOLD':pct>=70?'NEAR CAP':'HEALTHY'}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-hd"><h3>Notes</h3><span className="mono muted" style={{fontSize:10}}>editable</span></div>
          <div className="card-bd">
            <textarea className="txt" rows={4} value={note} onChange={e=>setNote(e.target.value)} placeholder="// operator notes…" style={{resize:'vertical', minHeight:80}}/>
            <div className="hstack" style={{justifyContent:'flex-end', marginTop:8}}>
              <Button size="sm" onClick={()=>toast.push('ok','Notes saved')} bracket>save</Button>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd">
          <h3>Cost breakdown · SKU</h3>
          <a href="#/costs" onClick={e=>{e.preventDefault();navigate('/costs');}}>open in explorer →</a>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>SKU</th><th className="num">MTD</th><th className="num">Previous</th><th className="num">Δ</th><th>Trend</th>
            </tr></thead>
            <tbody>
              {projectCosts.map(c => (
                <tr key={c.id}>
                  <td className="mono">{c.sku}</td>
                  <td className="num mono">{money(c.mtd)}</td>
                  <td className="num mono muted">{money(c.prev)}</td>
                  <td className="num"><CostDelta value={c.delta}/></td>
                  <td style={{width:160}}>
                    <Sparkline seed={c.id.length} up={c.delta>0}/>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>Total</td>
                <td className="num mono">{money(projectCosts.reduce((s,c)=>s+c.mtd,0))}</td>
                <td className="num mono muted">{money(projectCosts.reduce((s,c)=>s+c.prev,0))}</td>
                <td></td><td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

function Sparkline({ seed=1, up=true }) {
  const pts = Array.from({length:12}).map((_,i) => {
    const n = Math.sin(seed+i*0.9)*0.3 + Math.cos(i*0.5)*0.2 + (up?i*0.08:-i*0.06);
    return { x: i, y: n };
  });
  const miny = Math.min(...pts.map(p=>p.y));
  const maxy = Math.max(...pts.map(p=>p.y));
  const w = 140, h = 28;
  const xs = pts.map(p => (p.x/(pts.length-1))*w);
  const ys = pts.map(p => h - ((p.y - miny)/(maxy-miny+0.001))*h);
  const path = xs.map((x,i) => `${i===0?'M':'L'}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={path} fill="none" stroke={up?'var(--danger)':'var(--accent)'} strokeWidth="1.5"/>
    </svg>
  );
}

// ---------- COST EXPLORER ----------
function CostsPage() {
  const D = window.FinnaData;
  const [tab, setTab] = uS('overview');
  const [providers, setProviders] = uS({ azure:true, gcp:true, llm:true });
  const [projSel, setProjSel] = uS([]);  // project slugs
  const [sku, setSku] = uS('');
  const [applied, setApplied] = uS({ providers:{azure:true,gcp:true,llm:true}, proj:[], sku:'' });

  const apply = () => setApplied({ providers:{...providers}, proj:[...projSel], sku });
  const reset = () => { setProviders({azure:true,gcp:true,llm:true}); setProjSel([]); setSku(''); setApplied({providers:{azure:true,gcp:true,llm:true}, proj:[], sku:''}); };

  const filtered = D.COSTS.filter(c => applied.providers[c.prov] && (!applied.sku || c.sku.toLowerCase().includes(applied.sku.toLowerCase())) && (applied.proj.length===0 || applied.proj.includes(c.name)));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Cost explorer</h1>
          <div className="sub">// {filtered.length} records · normalized USD · source · cost_records</div>
        </div>
        <div className="actions">
          <Button icon="filter" bracket>add filter</Button>
          <Button icon="download" variant="primary" bracket>export csv</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <h3>Filters</h3>
          <div className="hstack">
            <Button size="sm" onClick={reset} bracket>reset</Button>
            <Button size="sm" variant="primary" onClick={apply} bracket>apply filters</Button>
          </div>
        </div>
        <div className="card-bd">
          <div className="row" style={{gridTemplateColumns:'auto 1fr 1fr', alignItems:'start'}}>
            <div>
              <div className="label">providers</div>
              <div className="stack stack-2">
                {['azure','gcp','llm'].map(p => (
                  <label key={p} className="checkbox">
                    <input type="checkbox" checked={providers[p]} onChange={e=>setProviders(s=>({...s,[p]:e.target.checked}))}/>
                    <span className="box"/>
                    <ProviderBadge p={p}/>
                    <span className="mono">{p}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <div className="label">projects</div>
              <div className="stack stack-2" style={{maxHeight:120, overflowY:'auto', border:'1px solid var(--border)', padding:8, background:'var(--bg)'}}>
                {D.PROJECTS.map(p => (
                  <label key={p.id} className="checkbox">
                    <input type="checkbox" checked={projSel.includes(p.name)} onChange={e=>{
                      setProjSel(s => e.target.checked ? [...s, p.name] : s.filter(x=>x!==p.name));
                    }}/>
                    <span className="box"/>
                    <ProviderBadge p={p.provider}/>
                    <span className="mono">{p.name}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <div className="label">SKU search</div>
              <div className="inp-group">
                <Icon name="search" size={14}/>
                <input className="inp" placeholder="e.g. BigQuery, VM, Tokens…" value={sku} onChange={e=>setSku(e.target.value)}/>
              </div>
              <div className="hint">// applies after [apply filters]</div>
              <div className="mt-3">
                <div className="label">date range</div>
                <div className="chip" style={{display:'inline-flex'}}><Icon name="calendar" size={12}/>&nbsp;Apr 1 – Apr 24, 2026</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="tabs mt-4">
        {[['overview','Overview'],['sku','By SKU'],['daily','Daily trend']].map(([k,l]) => (
          <button key={k} className={`tab ${tab===k?'active':''}`} onClick={()=>setTab(k)}>{l}</button>
        ))}
      </div>

      {tab==='overview' && <CostsOverview rows={filtered}/>}
      {tab==='sku' && <CostsBySku rows={filtered}/>}
      {tab==='daily' && <CostsDaily providers={applied.providers}/>}
    </div>
  );
}

function CostsOverview({ rows }) {
  const totals = rows.reduce((acc, r) => {
    acc[r.prov] = (acc[r.prov] || 0) + r.mtd;
    acc.prev[r.prov] = (acc.prev[r.prov] || 0) + r.prev;
    return acc;
  }, { prev:{} });
  const grand = rows.reduce((s,r)=>s+r.mtd, 0);
  const grandPrev = rows.reduce((s,r)=>s+r.prev, 0);
  return (
    <div className="card">
      <div className="card-hd">
        <h3>Records</h3>
        <span className="mono muted" style={{fontSize:11}}>{rows.length} rows · sum · {money(grand)}</span>
      </div>
      <div className="card-bd p0">
        {rows.length === 0 ? <EmptyState icon="search-x" title="No records" message="no cost records match your filters"/> : (
          <table className="tbl">
            <thead><tr>
              <th>Provider</th><th>Project</th><th>SKU</th>
              <th className="num">MTD</th><th className="num">Previous</th><th className="num">Δ</th>
            </tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td><ProviderBadge p={r.prov}/></td>
                  <td className="mono">{r.name}</td>
                  <td>{r.sku}</td>
                  <td className="num mono">{money(r.mtd)}</td>
                  <td className="num mono muted">{money(r.prev)}</td>
                  <td className="num"><CostDelta value={r.delta}/></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {['azure','gcp','llm'].map(p => totals[p] > 0 && (
                <tr key={p}>
                  <td colSpan={3}><span className="hstack"><ProviderBadge p={p}/><span className="uppercase mono" style={{fontSize:10}}>{p} subtotal</span></span></td>
                  <td className="num mono">{money(totals[p])}</td>
                  <td className="num mono muted">{money(totals.prev[p]||0)}</td>
                  <td className="num"><CostDelta value={totals.prev[p] ? ((totals[p]-totals.prev[p])/totals.prev[p]*100) : 0}/></td>
                </tr>
              ))}
              <tr>
                <td colSpan={3}><b style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase'}}>Grand total</b></td>
                <td className="num mono"><b>{money(grand)}</b></td>
                <td className="num mono muted">{money(grandPrev)}</td>
                <td className="num"><CostDelta value={grandPrev ? ((grand-grandPrev)/grandPrev*100) : 0}/></td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>
    </div>
  );
}

function CostsBySku({ rows }) {
  const grouped = {};
  rows.forEach(r => {
    const key = r.sku;
    if (!grouped[key]) grouped[key] = { sku:r.sku, count:0, mtd:0, prev:0, providers:new Set() };
    grouped[key].count++;
    grouped[key].mtd += r.mtd;
    grouped[key].prev += r.prev;
    grouped[key].providers.add(r.prov);
  });
  const out = Object.values(grouped).sort((a,b) => b.mtd - a.mtd);
  return (
    <div className="card">
      <div className="card-hd"><h3>Grouped by SKU</h3><span className="mono muted" style={{fontSize:11}}>{out.length} SKUs</span></div>
      <div className="card-bd p0">
        <table className="tbl">
          <thead><tr>
            <th>SKU</th><th>Providers</th><th className="num">Instances</th>
            <th className="num">MTD</th><th className="num">Previous</th><th className="num">Δ</th>
          </tr></thead>
          <tbody>
            {out.map(g => (
              <tr key={g.sku}>
                <td className="mono">{g.sku}</td>
                <td><span className="hstack">{[...g.providers].map(p => <ProviderBadge key={p} p={p}/>)}</span></td>
                <td className="num mono">{g.count}</td>
                <td className="num mono">{money(g.mtd)}</td>
                <td className="num mono muted">{money(g.prev)}</td>
                <td className="num"><CostDelta value={g.prev ? ((g.mtd-g.prev)/g.prev*100) : 0}/></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CostsDaily({ providers }) {
  const D = window.FinnaData;
  const series = [];
  if (providers.azure) series.push({ name:'Azure', color:'var(--azure)', data: D.DAILY.azure.map(d=>({label:d.label, value:d.value})) });
  if (providers.gcp) series.push({ name:'GCP', color:'var(--gcp)', data: D.DAILY.gcp.map(d=>({label:d.label, value:d.value})) });
  if (providers.llm) series.push({ name:'LLM', color:'var(--llm)', data: D.DAILY.llm.map(d=>({label:d.label, value:d.value})) });
  return (
    <div className="card">
      <div className="card-hd"><h3>Daily · stacked by provider</h3><span className="chip on">30 days</span></div>
      <div className="card-bd">
        {series.length === 0 ? <EmptyState icon="chart-line" message="select at least one provider"/> :
          <StackedAreaChart series={series} width={960} height={300}/>}
      </div>
    </div>
  );
}

Object.assign(window, { LoginPage, DashboardPage, ProjectsListPage, ProjectDetailPage, CostsPage });
