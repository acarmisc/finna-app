// Pages part 2: Configs (list + stepped create), Extractors, Alerts, Settings
const { useState: uS2, useEffect: uE2 } = React;

// ---------- CONFIGS LIST ----------
function ConfigsListPage() {
  const D = window.FinnaData;
  const toast = useToast();
  const [testing, setTesting] = uS2(null);
  const [results, setResults] = uS2({});
  const [confirmDel, setConfirmDel] = uS2(null);

  const testConn = (c) => {
    setTesting(c.id);
    setTimeout(() => {
      setTesting(null);
      const ok = c.last_test !== 'err';
      setResults(r => ({ ...r, [c.id]: ok ? 'ok' : 'err' }));
      toast.push(ok?'ok':'err', ok ? `Connection ${c.name} · OK` : `Connection ${c.name} failed · ${c.err || 'unknown error'}`);
      setTimeout(() => setResults(r => ({ ...r, [c.id]: null })), 2200);
    }, 900);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Cloud configs</h1>
          <div className="sub">// {D.CONFIGS.length} configured · 2 test failures in last 24h</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket onClick={()=>navigate('/configs/new')}>new config</Button>
        </div>
      </div>

      <div className="row row-3">
        {D.CONFIGS.map(c => {
          const flash = results[c.id];
          return (
            <div key={c.id} className="card" style={{position:'relative', borderColor: flash==='ok'?'var(--accent)':flash==='err'?'var(--danger)':'var(--border)', transition:'border-color 150ms'}}>
              <div className="card-hd">
                <div>
                  <h3 style={{color:'var(--fg)', textTransform:'none', letterSpacing:0, fontFamily:'Inter, sans-serif', fontSize:14, fontWeight:600}}>{c.name}</h3>
                  <div className="mono muted" style={{fontSize:10, marginTop:2}}>{c.credential_type}</div>
                </div>
                <ProviderBadge p={c.provider} size="lg"/>
              </div>
              <div className="card-bd">
                <dl style={{margin:0, fontSize:12, display:'grid', gridTemplateColumns:'auto 1fr', gap:'6px 12px'}}>
                  {c.tenant_id && <><dt className="mono muted" style={{fontSize:10}}>TENANT</dt><dd className="mono" style={{margin:0}}>{c.tenant_id}</dd></>}
                  {c.subscription_id && <><dt className="mono muted" style={{fontSize:10}}>SUB</dt><dd className="mono" style={{margin:0}}>{c.subscription_id}</dd></>}
                  {c.project_id && <><dt className="mono muted" style={{fontSize:10}}>PROJECT</dt><dd className="mono" style={{margin:0}}>{c.project_id}</dd></>}
                  <dt className="mono muted" style={{fontSize:10}}>CREATED</dt><dd className="mono" style={{margin:0}}>{c.created_at}</dd>
                  <dt className="mono muted" style={{fontSize:10}}>LAST TEST</dt>
                  <dd style={{margin:0}}><span className="hstack"><StatusBadge status={c.last_test}/><span className="mono muted" style={{fontSize:11}}>{c.last_test_at}</span></span></dd>
                </dl>
                {c.err && (
                  <div style={{marginTop:10, padding:'8px 10px', background:'color-mix(in oklab, var(--danger) 12%, var(--surface))', border:'1px solid var(--danger)', fontFamily:'JetBrains Mono, monospace', fontSize:11, color:'var(--danger)'}}>
                    // {c.err}
                  </div>
                )}
              </div>
              <div className="card-ft">
                <div className="hstack">
                  <Button size="sm" icon="edit-3" bracket onClick={()=>navigate(`/configs/${c.id}`)}>edit</Button>
                  <Button size="sm" icon={testing===c.id?'loader':'activity'} bracket onClick={()=>testConn(c)} disabled={testing===c.id}>{testing===c.id?'testing…':'test'}</Button>
                </div>
                <Button size="sm" variant="ghost" icon="trash-2" onClick={()=>setConfirmDel(c)}>delete</Button>
              </div>
            </div>
          );
        })}
      </div>

      <Dialog open={!!confirmDel} onClose={()=>setConfirmDel(null)} title={`Delete config · ${confirmDel?.name || ''}`}
        actions={<>
          <Button onClick={()=>setConfirmDel(null)} bracket>cancel</Button>
          <Button variant="danger" bracket onClick={()=>{ toast.push('ok', `Deleted ${confirmDel.name}`); setConfirmDel(null); }}>delete</Button>
        </>}>
        <p>This will remove the config and stop all scheduled extractions using it. Historical cost records remain.</p>
        <p className="mono" style={{color:'var(--danger)', marginTop:12}}>// this action cannot be undone</p>
      </Dialog>
    </div>
  );
}

// ---------- CONFIG CREATE (stepped) ----------
function ConfigCreatePage() {
  const [step, setStep] = uS2(1);
  const [prov, setProv] = uS2(null);
  const [cred, setCred] = uS2('service_principal');
  const [fields, setFields] = uS2({ name:'', tenant_id:'', client_id:'', client_secret:'', subscription_id:'', project_id:'', key_file:'' });
  const toast = useToast();

  const set = (k, v) => setFields(f => ({ ...f, [k]: v }));

  const canNext =
    (step === 1 && prov) ||
    (step === 2 && (
      prov === 'azure'
        ? (cred === 'service_principal' ? (fields.name && fields.tenant_id && fields.client_id && fields.client_secret && fields.subscription_id) : (fields.name && fields.subscription_id))
        : (fields.name && fields.project_id && (cred !== 'service_principal' || fields.key_file))
    )) ||
    step === 3;

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <a href="#/configs" onClick={e=>{e.preventDefault();navigate('/configs');}} style={{fontSize:11, fontFamily:'JetBrains Mono, monospace', color:'var(--fg-muted)'}}>← configs</a>
          <h1 style={{marginTop:6}}>New cloud config</h1>
          <div className="sub">// 3-step setup · POST /api/v1/config</div>
        </div>
      </div>

      <div className="steps">
        <span className={`step ${step>1?'done':step===1?'on':''}`}><span className="n">{step>1?'✓':'1'}</span>provider</span>
        <span className="sep">→</span>
        <span className={`step ${step>2?'done':step===2?'on':''}`}><span className="n">{step>2?'✓':'2'}</span>credentials</span>
        <span className="sep">→</span>
        <span className={`step ${step===3?'on':''}`}><span className="n">3</span>review</span>
      </div>

      <div className="card">
        <div className="card-bd" style={{padding:24}}>
          {step===1 && (
            <div>
              <div className="label">select a provider</div>
              <div className="row row-2" style={{marginTop:8}}>
                {[
                  { id:'azure', title:'Microsoft Azure', desc:'Cost Management export · subscription or RG scope', color:'var(--azure)' },
                  { id:'gcp',   title:'Google Cloud',    desc:'BigQuery billing export · project scope', color:'var(--gcp)' },
                ].map(p => (
                  <button key={p.id} onClick={()=>setProv(p.id)}
                    style={{
                      padding:20, textAlign:'left', cursor:'pointer',
                      background: prov===p.id ? 'color-mix(in oklab, '+p.color+' 10%, var(--surface))' : 'var(--surface)',
                      border: `1px solid ${prov===p.id ? p.color : 'var(--border)'}`,
                      boxShadow: prov===p.id ? `inset 0 0 0 1px ${p.color}` : 'none',
                      color:'inherit', font:'inherit', display:'flex', flexDirection:'column', gap:12,
                    }}>
                    <div className="hstack spread">
                      <ProviderBadge p={p.id} size="lg"/>
                      {prov===p.id && <span className="mono" style={{fontSize:10, color:p.color, textTransform:'uppercase', letterSpacing:'0.1em'}}>✓ selected</span>}
                    </div>
                    <div>
                      <div style={{fontSize:15, fontWeight:600, color:'var(--fg)'}}>{p.title}</div>
                      <div className="mono muted" style={{fontSize:11, marginTop:4}}>{p.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step===2 && prov==='azure' && (
            <div className="stack stack-4">
              <div>
                <div className="label">credential type</div>
                <select className="sel" value={cred} onChange={e=>setCred(e.target.value)}>
                  <option value="service_principal">service_principal</option>
                  <option value="managed_identity">managed_identity</option>
                  <option value="cli">cli</option>
                  <option value="device_code">device_code</option>
                </select>
              </div>
              <div><div className="label">name *</div><input className="inp" placeholder="acme-prod-azure" value={fields.name} onChange={e=>set('name', e.target.value)}/></div>
              {cred==='service_principal' && <>
                <div><div className="label">tenant id *</div><input className="inp" placeholder="8f2c-…-a1e9" value={fields.tenant_id} onChange={e=>set('tenant_id', e.target.value)}/></div>
                <div className="row row-2">
                  <div><div className="label">client id *</div><input className="inp" value={fields.client_id} onChange={e=>set('client_id', e.target.value)}/></div>
                  <div><div className="label">client secret *</div><input type="password" className="inp" value={fields.client_secret} onChange={e=>set('client_secret', e.target.value)}/></div>
                </div>
              </>}
              <div><div className="label">subscription id *</div><input className="inp" placeholder="00000000-0000-0000-…" value={fields.subscription_id} onChange={e=>set('subscription_id', e.target.value)}/></div>
            </div>
          )}

          {step===2 && prov==='gcp' && (
            <div className="stack stack-4">
              <div>
                <div className="label">credential type</div>
                <select className="sel" value={cred} onChange={e=>setCred(e.target.value)}>
                  <option value="service_principal">service account key</option>
                  <option value="cli">cli (gcloud adc)</option>
                </select>
              </div>
              <div><div className="label">name *</div><input className="inp" placeholder="prod-platform-gcp" value={fields.name} onChange={e=>set('name', e.target.value)}/></div>
              <div><div className="label">project id *</div><input className="inp" placeholder="acme-prod-platform" value={fields.project_id} onChange={e=>set('project_id', e.target.value)}/></div>
              {cred==='service_principal' && (
                <div>
                  <div className="label">service account key (JSON) *</div>
                  <div style={{border:'1px dashed var(--border)', padding:16, background:'var(--bg)', textAlign:'center', fontFamily:'JetBrains Mono, monospace', fontSize:11, color:'var(--fg-muted)'}}>
                    <Icon name="upload" size={16}/>
                    <div style={{marginTop:6}}>{fields.key_file ? <span style={{color:'var(--accent)'}}>✓ {fields.key_file}</span> : 'drop key.json here or click to select'}</div>
                    <Button size="sm" bracket onClick={()=>set('key_file', 'sa-acme-prod.json')} style={{marginTop:10}}>browse</Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {step===3 && (
            <div>
              <div className="label">review</div>
              <div style={{border:'1px solid var(--border)', background:'var(--bg)', padding:16, fontFamily:'JetBrains Mono, monospace', fontSize:12}}>
                <div style={{color:'var(--fg-subtle)'}}># POST /api/v1/config</div>
                <pre style={{margin:0, marginTop:8, color:'var(--fg)', whiteSpace:'pre-wrap', lineHeight:1.6}}>{JSON.stringify({
  name: fields.name, provider: prov, credential_type: cred,
  ...(prov==='azure' ? {
    tenant_id: fields.tenant_id || '(unset)',
    client_id: fields.client_id || '(unset)',
    client_secret: fields.client_secret ? '••••••••' : '(unset)',
    subscription_id: fields.subscription_id
  } : {
    project_id: fields.project_id,
    key_file: fields.key_file || '(unset)'
  })
                }, null, 2)}</pre>
              </div>
              <div className="hint" style={{marginTop:10}}>// secrets are encrypted at rest · stored in cloud_config table</div>
            </div>
          )}
        </div>
        <div className="card-ft">
          <Button bracket disabled={step===1} onClick={()=>setStep(s => Math.max(1, s-1))}>← back</Button>
          {step < 3
            ? <Button variant="primary" bracket disabled={!canNext} onClick={()=>setStep(s => s+1)}>next step →</Button>
            : <Button variant="primary" bracket icon="check" onClick={()=>{ toast.push('ok', `Config ${fields.name} created`); navigate('/configs'); }}>create config</Button>}
        </div>
      </div>
    </div>
  );
}

// ---------- EXTRACTORS ----------
function ExtractorsPage() {
  const D = window.FinnaData;
  const [sel, setSel] = uS2(D.CONFIGS[0].id);
  const [extType, setExtType] = uS2('');
  const [runs, setRuns] = uS2(D.RUNS);
  const [newRun, setNewRun] = uS2(null);
  const [expanded, setExpanded] = uS2(null);
  const toast = useToast();

  // Simulate status polling on newRun
  uE2(() => {
    if (!newRun) return;
    const t = setInterval(() => {
      setRuns(rs => rs.map(r => {
        if (r.run_id === newRun) {
          if (r.status === 'started') return { ...r, status: 'running' };
          if (r.status === 'running') return { ...r, status: 'completed', duration: '38s', finished_at: 'just now', records_extracted: 1284 };
        }
        return r;
      }));
    }, 2500);
    return () => clearInterval(t);
  }, [newRun]);

  const trigger = () => {
    const cfg = D.CONFIGS.find(c => c.id === sel);
    const id = 'r_' + Date.now().toString(36).slice(-8);
    const run = {
      run_id: id, extractor_type: extType || `${cfg.provider}_cost`, provider: cfg.provider,
      status: 'started', started_at: 'just now', finished_at: null,
      records_extracted: 0, duration: '—', config_id: cfg.id,
    };
    setRuns(rs => [run, ...rs]);
    setNewRun(id);
    toast.push('info', `Started run ${id} · ${run.extractor_type}`);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Extractors</h1>
          <div className="sub">// {runs.length} runs · auto-refresh every 10s · extractor_runs table</div>
        </div>
        <div className="actions">
          <Button icon="refresh-ccw" bracket>refresh</Button>
        </div>
      </div>

      <div className="row" style={{gridTemplateColumns:'40% 1fr'}}>
        <div className="card" style={{alignSelf:'start'}}>
          <div className="card-hd"><h3>Trigger run</h3><span className="chip">POST /extractors/run</span></div>
          <div className="card-bd stack stack-4">
            <div>
              <div className="label">config *</div>
              <select className="sel" value={sel} onChange={e=>setSel(e.target.value)}>
                {D.CONFIGS.map(c => (
                  <option key={c.id} value={c.id}>{c.name}  ·  {c.provider}</option>
                ))}
              </select>
            </div>
            <div>
              <div className="label">extractor type (optional)</div>
              <input className="inp" placeholder="e.g. azure_cost, gcp_billing" value={extType} onChange={e=>setExtType(e.target.value)}/>
              <div className="hint">// blank · defaults based on provider</div>
            </div>
            <div>
              <Button variant="primary" block bracket icon="play" onClick={trigger}>run extractor</Button>
            </div>
            {newRun && (
              <div style={{padding:12, background:'var(--bg)', border:'1px solid var(--border)'}}>
                <div className="stat-lbl">polling</div>
                <div className="mono" style={{marginTop:4, fontSize:12}}>run_id · <b>{newRun}</b></div>
                <div className="mt-2"><StatusBadge status={runs.find(r=>r.run_id===newRun)?.status || 'started'}/></div>
                <div className="hint mt-2">// GET /extractors/status?run_id={newRun} · every 3s</div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-hd">
            <h3>Run history</h3>
            <div className="hstack">
              <span className="chip">status: <b>all</b></span>
              <span className="chip">provider: <b>all</b></span>
            </div>
          </div>
          <div className="card-bd p0" style={{maxHeight: 640, overflowY:'auto'}}>
            <table className="tbl">
              <thead><tr>
                <th>Status</th><th>Run ID</th><th>Extractor</th><th>Provider</th>
                <th>Started</th><th>Finished</th><th className="num">Records</th><th className="num">Duration</th>
              </tr></thead>
              <tbody>
                {runs.map(r => (
                  <React.Fragment key={r.run_id}>
                    <tr className="clickable" onClick={()=>setExpanded(e => e===r.run_id ? null : r.run_id)}>
                      <td><StatusBadge status={r.status}/></td>
                      <td><span className="id">{r.run_id}</span></td>
                      <td className="mono">{r.extractor_type}</td>
                      <td><ProviderBadge p={r.provider}/></td>
                      <td className="mono muted">{r.started_at}</td>
                      <td className="mono muted">{r.finished_at || '—'}</td>
                      <td className="num mono">{r.records_extracted ? r.records_extracted.toLocaleString() : '—'}</td>
                      <td className="num mono">{r.duration}</td>
                    </tr>
                    {expanded === r.run_id && (
                      <tr>
                        <td colSpan={8} style={{background:'var(--bg)', padding:16}}>
                          <div className="row row-2">
                            <div>
                              <div className="label">run details</div>
                              <pre className="mono" style={{fontSize:11, margin:0, background:'var(--surface)', border:'1px solid var(--border)', padding:10, color:'var(--fg)'}}>{JSON.stringify({run_id:r.run_id, extractor:r.extractor_type, provider:r.provider, config_id:r.config_id, status:r.status, records:r.records_extracted, duration:r.duration}, null, 2)}</pre>
                            </div>
                            <div>
                              <div className="label">error / stderr</div>
                              {r.error_message
                                ? <pre className="mono" style={{fontSize:11, margin:0, background:'color-mix(in oklab, var(--danger) 10%, var(--surface))', border:'1px solid var(--danger)', padding:10, color:'var(--danger)'}}>{r.error_message}</pre>
                                : <div className="empty" style={{padding:16}}><div className="msg">no errors</div></div>}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- ALERTS ----------
function AlertsPage() {
  const D = window.FinnaData;
  const S = D.ALERT_STATS;
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Alerts</h1>
          <div className="sub">// 3 firing · 6 rules · source · alerts table</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket>new rule</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd"><h3>Stats · 30 days</h3></div>
        <div className="card-bd">
          <div className="hstack-4" style={{flexWrap:'wrap', gap:12}}>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>firing · <b style={{color:'var(--danger)'}}>{S.by_status.firing}</b></span>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>ack · <b style={{color:'var(--warning)'}}>{S.by_status.ack}</b></span>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>resolved · <b style={{color:'var(--accent)'}}>{S.by_status.resolved}</b></span>
            <span style={{width:1, height:16, background:'var(--border)'}}/>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>critical · <b style={{color:'var(--danger)'}}>{S.by_severity.critical}</b></span>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>warning · <b style={{color:'var(--warning)'}}>{S.by_severity.warning}</b></span>
            <span className="chip" style={{padding:'6px 12px', fontSize:12}}>info · <b style={{color:'var(--primary)'}}>{S.by_severity.info}</b></span>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd">
          <h3>Active + recent</h3>
          <div className="hstack">
            <span className="chip">status: <b>all</b></span>
            <span className="chip">severity: <b>all</b></span>
          </div>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>Status</th><th>Severity</th><th>Description</th><th>Project</th><th>Rule</th><th>Triggered</th><th></th>
            </tr></thead>
            <tbody>
              {D.ALERTS.map(a => (
                <tr key={a.id}>
                  <td><StatusBadge status={a.status}/></td>
                  <td><SeverityBadge severity={a.severity}/></td>
                  <td style={{maxWidth:360}}>{a.description}</td>
                  <td className="mono"><a href={`#/projects/${a.project}`} onClick={e=>{e.preventDefault();navigate(`/projects/${a.project}`);}}>{a.project}</a></td>
                  <td><code style={{fontSize:11, color:'var(--fg-muted)'}}>{a.rule}</code></td>
                  <td className="mono muted" style={{fontSize:11}}>{a.triggered_at}</td>
                  <td><div className="hstack"><Button size="sm" bracket>ack</Button><Button size="sm" variant="ghost" icon="more-horizontal"></Button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------- SETTINGS (placeholder) ----------
function SettingsPage() {
  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <div className="sub">// account, orchestrator, integrations</div>
        </div>
      </div>
      <div className="card">
        <div className="card-hd"><h3>Account</h3></div>
        <div className="card-bd stack stack-4">
          <div><div className="label">email</div><input className="inp" defaultValue="finops@acme.co"/></div>
          <div><div className="label">org</div><input className="inp" defaultValue="acme" disabled/></div>
          <div><div className="label">default currency</div>
            <select className="sel" defaultValue="USD"><option>USD</option><option>EUR</option><option>GBP</option></select>
          </div>
        </div>
        <div className="card-ft">
          <span className="mono muted" style={{fontSize:11}}>// changes apply on save</span>
          <Button variant="primary" bracket>save</Button>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd"><h3>Orchestrator</h3></div>
        <div className="card-bd stack stack-3">
          <div className="spread">
            <div>
              <div className="mono" style={{fontSize:12}}>api endpoint</div>
              <div className="mono muted" style={{fontSize:11}}>http://api.finna.dev</div>
            </div>
            <span className="badge ghost-accent"><span className="dot"/>healthy · 42ms</span>
          </div>
          <div className="hr"/>
          <div className="spread">
            <div>
              <div className="mono" style={{fontSize:12}}>scheduler</div>
              <div className="mono muted" style={{fontSize:11}}>nightly · 02:00 UTC</div>
            </div>
            <Button size="sm" bracket>edit schedule</Button>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd"><h3>Danger zone</h3></div>
        <div className="card-bd">
          <div className="spread">
            <div>
              <div style={{color:'var(--fg)', fontWeight:500}}>Purge cost records</div>
              <div className="mono muted" style={{fontSize:11, marginTop:4}}>// delete all cost_records older than retention window</div>
            </div>
            <Button variant="danger" bracket icon="trash-2">purge</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ConfigsListPage, ConfigCreatePage, ExtractorsPage, AlertsPage, SettingsPage });
