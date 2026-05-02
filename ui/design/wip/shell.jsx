// AppShell — sidebar + topbar + hash routing
const { useState: useS, useEffect: useE } = React;

const NAV = [
  { sec:'Overview' },
  { id:'dashboard', label:'Dashboard', icon:'layout-dashboard', path:'/dashboard' },
  { id:'costs',     label:'Cost explorer', icon:'chart-line', path:'/costs' },
  { sec:'Resources' },
  { id:'projects',  label:'Projects', icon:'folders', path:'/projects' },
  { id:'configs',   label:'Cloud configs', icon:'plug', path:'/configs' },
  { id:'extractors',label:'Extractors', icon:'database', path:'/extractors' },
  { sec:'Monitoring' },
  { id:'alerts',    label:'Alerts', icon:'bell', path:'/alerts', countKey:'alerts' },
  { id:'settings',  label:'Settings', icon:'settings-2', path:'/settings' },
];

function useHashRoute() {
  const [route, setRoute] = useS(() => parseHash());
  useE(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
function parseHash() {
  const raw = window.location.hash.replace(/^#/, '') || '/dashboard';
  const [path, query=''] = raw.split('?');
  const parts = path.split('/').filter(Boolean);
  const base = '/' + (parts[0] || 'dashboard');
  const sub = parts[1] || null;
  const qs = new URLSearchParams(query);
  return { path, base, sub, parts, qs };
}
function navigate(p) { window.location.hash = p; }

function Sidebar({ collapsed, onToggle, activeBase, onLogout }) {
  const [menu, setMenu] = useS(false);
  const counts = { alerts: 3 };
  return (
    <aside className="sb">
      <div className="sb-logo" onClick={onToggle} title={collapsed?'Expand':'Collapse'}>
        <span className="caret">&gt;</span>
        <span className="wordmark">finna</span>
        <span className="cursor" />
      </div>
      <nav className="sb-nav">
        {NAV.map((item, i) => {
          if (item.sec) return <div key={i} className="sb-section">{item.sec}</div>;
          const active = activeBase === item.path;
          return (
            <a key={item.id} className={`sb-item ${active?'active':''}`} onClick={(e)=>{e.preventDefault(); navigate(item.path);}} href={`#${item.path}`}>
              <Icon name={item.icon} size={16}/>
              <span className="label">{item.label}</span>
              {item.countKey && counts[item.countKey] > 0 && <span className="count">{counts[item.countKey]}</span>}
            </a>
          );
        })}
      </nav>
      <div className="sb-foot" style={{position:'relative'}}>
        <div className="avatar">FN</div>
        <div className="who">
          <div className="name">finops@acme.co</div>
          <div className="org">API · healthy</div>
        </div>
        <span className="health" title="API healthy" />
        <button className="icon-btn" onClick={()=>setMenu(m=>!m)} title="Account">
          <Icon name="chevron-up" size={14}/>
        </button>
        {menu && (
          <div style={{position:'absolute', bottom:'calc(100% + 4px)', right:8, left:8, background:'var(--surface)', border:'1px solid var(--border)', boxShadow:'0 4px 0 rgba(0,0,0,0.3)', zIndex:20}}>
            <a href="#/settings" onClick={(e)=>{e.preventDefault(); setMenu(false); navigate('/settings');}} style={{display:'flex', alignItems:'center', gap:8, padding:'8px 12px', fontSize:12, color:'var(--fg)', borderBottom:'1px solid var(--border-2)', cursor:'pointer'}}>
              <Icon name="settings-2" size={14}/><span>Settings</span>
            </a>
            <a onClick={()=>{ setMenu(false); onLogout && onLogout(); }} style={{display:'flex', alignItems:'center', gap:8, padding:'8px 12px', fontSize:12, color:'var(--danger)', cursor:'pointer', fontFamily:'JetBrains Mono, monospace'}}>
              <Icon name="log-out" size={14}/><span>Log out</span>
            </a>
          </div>
        )}
      </div>
    </aside>
  );
}

function DateRangePicker({ range, setRange, customRange, setCustomRange, label }) {
  const [open, setOpen] = useS(false);
  const [viewMonth, setViewMonth] = useS(() => {
    const d = customRange?.start ? new Date(customRange.start) : new Date(2026, 3, 1);
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [draftStart, setDraftStart] = useS(customRange?.start || null);
  const [draftEnd, setDraftEnd] = useS(customRange?.end || null);
  const ref = React.useRef(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const fmt = (iso) => {
    if (!iso) return '—';
    const [y,m,d] = iso.split('-').map(Number);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[m-1]} ${d}, ${y}`;
  };
  const toIso = (y, m, d) => `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;

  const presets = [
    ['mtd','Month to date'],
    ['7d','Last 7 days'],
    ['30d','Last 30 days'],
    ['90d','Last 90 days'],
  ];

  const pickPreset = (k) => {
    setRange(k);
    setCustomRange(null);
    setDraftStart(null); setDraftEnd(null);
    setOpen(false);
  };

  const onDayClick = (iso) => {
    if (!draftStart || (draftStart && draftEnd)) {
      setDraftStart(iso); setDraftEnd(null);
    } else {
      if (iso < draftStart) { setDraftEnd(draftStart); setDraftStart(iso); }
      else setDraftEnd(iso);
    }
  };

  const applyCustom = () => {
    if (draftStart && draftEnd) {
      setCustomRange({ start: draftStart, end: draftEnd });
      setRange('custom');
      setOpen(false);
    }
  };

  const daysInMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth()+1, 0).getDate();
  const firstDay = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1).getDay(); // 0=Sun
  const shiftMonth = (n) => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth()+n, 1));
  const monthLabel = viewMonth.toLocaleString('en-US', { month:'long', year:'numeric' });

  const cells = [];
  for (let i=0;i<firstDay;i++) cells.push(null);
  for (let d=1; d<=daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const inRange = (iso) => draftStart && draftEnd && iso >= draftStart && iso <= draftEnd;
  const isEdge = (iso) => iso === draftStart || iso === draftEnd;

  return (
    <div style={{position:'relative'}} ref={ref}>
      <button className="tb-daterange" onClick={()=>setOpen(o=>!o)} title="Date range">
        <Icon name="calendar" size={12}/>
        <span>{label}</span>
        <Icon name="chevron-down" size={12}/>
      </button>
      {open && (
        <div style={{position:'absolute', top:'calc(100% + 6px)', right:0, background:'var(--surface)', border:'1px solid var(--border-strong)', boxShadow:'0 6px 0 rgba(0,0,0,0.35)', zIndex:100, display:'flex', fontFamily:'Inter, system-ui, sans-serif'}}>
          {/* presets */}
          <div style={{display:'flex', flexDirection:'column', borderRight:'1px solid var(--border)', minWidth:150, background:'var(--surface-2)'}}>
            {presets.map(([k,l]) => (
              <button key={k} onClick={()=>pickPreset(k)} style={{padding:'9px 14px', textAlign:'left', background: range===k?'var(--primary)':'transparent', color: range===k?'var(--primary-fg)':'var(--fg)', border:'none', borderBottom:'1px solid var(--border-2)', cursor:'pointer', fontSize:11, fontFamily:'JetBrains Mono, monospace', textTransform:'uppercase', letterSpacing:'0.06em'}}>{l}</button>
            ))}
            <div style={{padding:'9px 14px', fontSize:10, color:'var(--fg-subtle)', fontFamily:'JetBrains Mono, monospace', textTransform:'uppercase', letterSpacing:'0.08em', borderTop:'1px solid var(--border)'}}>// custom →</div>
          </div>
          {/* calendar */}
          <div style={{padding:12, minWidth:260}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:8}}>
              <button onClick={()=>shiftMonth(-1)} style={{width:22, height:22, border:'1px solid var(--border)', background:'var(--surface-2)', color:'var(--fg-muted)', cursor:'pointer'}}>‹</button>
              <div style={{fontFamily:'JetBrains Mono, monospace', fontSize:11, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--fg)'}}>{monthLabel}</div>
              <button onClick={()=>shiftMonth(1)} style={{width:22, height:22, border:'1px solid var(--border)', background:'var(--surface-2)', color:'var(--fg-muted)', cursor:'pointer'}}>›</button>
            </div>
            <div style={{display:'grid', gridTemplateColumns:'repeat(7, 1fr)', gap:2, marginBottom:4}}>
              {['S','M','T','W','T','F','S'].map((d,i)=>(
                <div key={i} style={{textAlign:'center', fontSize:9, color:'var(--fg-subtle)', fontFamily:'JetBrains Mono, monospace', padding:'2px 0'}}>{d}</div>
              ))}
            </div>
            <div style={{display:'grid', gridTemplateColumns:'repeat(7, 1fr)', gap:2}}>
              {cells.map((d, i) => {
                if (d === null) return <div key={i} style={{height:26}}/>;
                const iso = toIso(viewMonth.getFullYear(), viewMonth.getMonth(), d);
                const edge = isEdge(iso);
                const mid = inRange(iso) && !edge;
                return (
                  <button key={i} onClick={()=>onDayClick(iso)} style={{height:26, border:'1px solid '+(edge?'var(--primary)':'transparent'), background: edge?'var(--primary)':mid?'var(--surface-3)':'transparent', color: edge?'var(--primary-fg)':'var(--fg)', cursor:'pointer', fontFamily:'JetBrains Mono, monospace', fontSize:11}}>{d}</button>
                );
              })}
            </div>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginTop:10, paddingTop:10, borderTop:'1px solid var(--border)', gap:8}}>
              <div style={{fontFamily:'JetBrains Mono, monospace', fontSize:10, color:'var(--fg-muted)'}}>
                {fmt(draftStart)} — {fmt(draftEnd)}
              </div>
              <button onClick={applyCustom} disabled={!draftStart || !draftEnd} style={{padding:'5px 10px', background: (draftStart&&draftEnd)?'var(--primary)':'var(--surface-2)', color:(draftStart&&draftEnd)?'var(--primary-fg)':'var(--fg-subtle)', border:'1px solid '+((draftStart&&draftEnd)?'var(--primary)':'var(--border)'), cursor:(draftStart&&draftEnd)?'pointer':'not-allowed', fontFamily:'JetBrains Mono, monospace', fontSize:10, textTransform:'uppercase', letterSpacing:'0.08em'}}>[ apply ]</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Topbar({ route, theme, setTheme, range, setRange, customRange, setCustomRange }) {
  const labelFor = {
    dashboard:'Dashboard', projects:'Projects', configs:'Cloud configs',
    extractors:'Extractors', costs:'Cost explorer', alerts:'Alerts', settings:'Settings'
  };
  const key = route.base.replace('/','');
  const crumbs = [{ label:'finna', mono:true }, { label: labelFor[key] || key }];
  if (route.sub) crumbs.push({ label: route.sub, mono:true });
  const ranges = [['mtd','MTD'],['7d','7d'],['30d','30d'],['90d','90d']];
  const presetLabel = { mtd:'Apr 1 — Apr 24, 2026', '7d':'Apr 18 — Apr 24', '30d':'Mar 26 — Apr 24', '90d':'Jan 24 — Apr 24' }[range];
  const fmt = (iso) => {
    if (!iso) return '';
    const [y,m,d] = iso.split('-').map(Number);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[m-1]} ${d}`;
  };
  const customLabel = customRange ? `${fmt(customRange.start)} — ${fmt(customRange.end)}` : null;
  const label = range === 'custom' && customLabel ? customLabel : presetLabel;
  return (
    <header className="tb">
      <div className="tb-crumb">
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i>0 && <span className="sep">/</span>}
            <span className={`${i===crumbs.length-1?'last':''} ${c.mono?'mono':''}`}>{c.label}</span>
          </React.Fragment>
        ))}
      </div>
      <div className="tb-actions">
        <div style={{display:'flex', border:'1px solid var(--border)', background:'var(--surface-2)'}}>
          {ranges.map(([k,l]) => (
            <button key={k} onClick={()=>{ setRange(k); setCustomRange(null); }} style={{padding:'5px 9px', fontFamily:'JetBrains Mono, monospace', fontSize:10, letterSpacing:'0.08em', textTransform:'uppercase', background: range===k?'var(--primary)':'transparent', color: range===k?'var(--primary-fg)':'var(--fg-muted)', border:'none', borderRight:'1px solid var(--border)', cursor:'pointer'}}>{l}</button>
          ))}
        </div>
        <DateRangePicker range={range} setRange={setRange} customRange={customRange} setCustomRange={setCustomRange} label={label}/>
        <div className="sep-v"/>
        <button className="icon-btn" onClick={() => setTheme(theme==='dark'?'light':'dark')} title="Toggle theme">
          <Icon name={theme==='dark'?'sun':'moon'} size={14}/>
        </button>
        <button className="tb-bell" onClick={() => navigate('/alerts')} title="Alerts">
          <Icon name="bell" size={14}/>
          <span className="badge">3</span>
        </button>
      </div>
    </header>
  );
}

function AppShell({ theme, setTheme, onLogout, children }) {
  const route = useHashRoute();
  const [collapsed, setCollapsed] = useS(false);
  const [range, setRange] = useS('mtd');
  const [customRange, setCustomRange] = useS(null);
  window.__finnaRange = range;
  window.__finnaCustomRange = customRange;
  return (
    <div className={`app ${collapsed?'collapsed':''}`}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} activeBase={route.base} onLogout={onLogout} />
      <Topbar route={route} theme={theme} setTheme={setTheme} range={range} setRange={setRange} customRange={customRange} setCustomRange={setCustomRange} />
      <main className="main">{children(route, { range, customRange })}</main>
    </div>
  );
}

Object.assign(window, { AppShell, useHashRoute, navigate, parseHash });
