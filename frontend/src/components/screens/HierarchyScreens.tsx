import React, { useState, useMemo } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag, ProviderDot } from '../common/ProviderTag';
import { StatCard } from '../common/StatCard';
import { MiniBars } from '../common/MiniBars';
import { Icon } from '../common/Icon';
import { Breadcrumb } from '../common/Breadcrumb';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { Toast, Route, FinProject, Connection, Resource } from '../../types';

// ============================================================================
// PROJECTS LIST
// ============================================================================
interface ProjectsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onNav: (route: Route) => void;
  onNewProject: () => void;
}

export function ProjectsScreen({ pushToast, onNav, onNewProject }: ProjectsScreenProps) {
  const { FIN_PROJECTS, CONNECTIONS } = FINNA_DATA;
  const countConns = (pid: string) => CONNECTIONS.filter(c => c.projectId === pid).length;
  const countRes = (pid: string) => CONNECTIONS.filter(c => c.projectId === pid).reduce((a, c) => a + (c.resources?.length || 0), 0);
  const unassignedConns = CONNECTIONS.filter(c => !c.projectId);

  return (
    <div className="fn-screen" data-screen-label="Projects">
      <TopBar title="Projects"
        subtitle={`${FIN_PROJECTS.length} projects · ${CONNECTIONS.length} connections · ${unassignedConns.length} unassigned`}
        actions={<>
          <Button variant="outline" size="sm" icon="download">Export</Button>
          <Button variant="primary" size="sm" icon="plus" onClick={onNewProject}>New project</Button>
        </>}
      />
      <div className="fn-proj-grid">
        {FIN_PROJECTS.map(p => {
          const pct = p.mtd / p.budgetCap;
          const over = pct > 0.8;
          return (
            <div key={p.id} className="fn-panel fn-proj is-clickable"
              onClick={() => onNav({ screen: 'project', projectId: p.id })}>
              <div className="fn-proj-head">
                <div>
                  <div className="fn-proj-name">{p.name}</div>
                  <div className="fn-proj-slug mono">{p.slug} · {p.costCenter}</div>
                </div>
                <Badge tone={over ? 'err' : 'ok'} dot>{over ? 'Over 80%' : 'Healthy'}</Badge>
              </div>
              <div className="fn-proj-budget">
                <div className="fn-budget-bar">
                  <div className="fn-budget-fill" style={{ width: Math.min(pct, 1) * 100 + '%', background: over ? 'var(--danger)' : 'var(--primary)' }} />
                </div>
                <div className="fn-proj-budget-row">
                  <span className="mono fn-strong">{fmt.money(p.mtd)}</span>
                  <span className="fn-muted">of {fmt.money(p.budgetCap)} · {(pct * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="fn-proj-meta">
                <div><span className="fn-k">Connections</span><span className="fn-v mono">{countConns(p.id)}</span></div>
                <div><span className="fn-k">Resources</span><span className="fn-v mono">{countRes(p.id)}</span></div>
                <div><span className="fn-k">Owner</span><span className="fn-v mono">{p.owner}</span></div>
              </div>
              <div className="fn-proj-tags">
                {Object.entries(p.tags).map(([k, v]) => (
                  <span key={k} className="fn-chip fn-chip-sm">{k}: <b>{v}</b></span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      {unassignedConns.length > 0 && (
        <div className="fn-panel">
          <div className="fn-panel-head">
            <div>
              <h3>Unassigned connections</h3>
              <div className="fn-sub">Connections not bound to any project. Move them for budget governance.</div>
            </div>
          </div>
          <div className="fn-unassigned">
            {unassignedConns.map(c => (
              <div key={c.id} className="fn-unassigned-row">
                <ProviderDot p={c.prov} />
                <span className="mono fn-strong">{c.name}</span>
                <span className="fn-muted">{c.scope}</span>
                <Button variant="outline" size="xs" icon="folder-plus"
                  onClick={() => pushToast({ tone: 'info', title: 'Move connection', body: 'Select a project in the dialog (mocked).' })}>
                  Assign to project
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// PROJECT DETAIL
// ============================================================================
interface ProjectDetailScreenProps {
  projectId: string;
  onNav: (route: Route) => void;
  onNewConnection: (projectId: string) => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function ProjectDetailScreen({ projectId, onNav, onNewConnection, pushToast }: ProjectDetailScreenProps) {
  const { FIN_PROJECTS, CONNECTIONS } = FINNA_DATA;
  const p = FIN_PROJECTS.find(x => x.id === projectId);
  if (!p) return <div className="fn-screen"><TopBar title="Project not found" /></div>;

  const conns = CONNECTIONS.filter(c => c.projectId === projectId);
  const resourceCount = conns.reduce((a, c) => a + (c.resources?.length || 0), 0);
  const pct = p.mtd / p.budgetCap;

  return (
    <div className="fn-screen" data-screen-label={`Project · ${p.name}`}>
      <TopBar
        breadcrumb={<Breadcrumb items={[
          { label: 'Projects', onClick: () => onNav({ screen: 'projects' }) },
          { label: p.name },
        ]} />}
        title={p.name}
        subtitle={`${conns.length} connections · ${resourceCount} resources · cost center ${p.costCenter}`}
        actions={<>
          <Button variant="outline" size="sm" icon="tag"
            onClick={() => pushToast({ tone: 'info', title: 'Edit tags', body: 'Tag editor opened (mocked).' })}>
            Edit tags
          </Button>
          <Button variant="outline" size="sm" icon="pencil">Edit</Button>
          <Button variant="primary" size="sm" icon="plus" onClick={() => onNewConnection(p.id)}>New connection</Button>
        </>}
      />

      <div className="fn-proj-hero">
        <div className="fn-proj-hero-stat">
          <div className="fn-stat-lbl">Month to date</div>
          <div className="fn-stat-val">{fmt.money(p.mtd)}</div>
          <div className="fn-stat-delta fn-muted">of {fmt.money(p.budgetCap)} budget</div>
        </div>
        <div className="fn-proj-hero-stat">
          <div className="fn-stat-lbl">Utilization</div>
          <div className="fn-stat-val">{(pct * 100).toFixed(0)}<span style={{ fontSize: '0.5em', color: 'var(--fg-muted)' }}>%</span></div>
          <div className="fn-budget-bar" style={{ marginTop: 8 }}>
            <div className="fn-budget-fill" style={{ width: Math.min(pct, 1) * 100 + '%', background: pct > 0.8 ? 'var(--danger)' : 'var(--primary)' }} />
          </div>
        </div>
        <div className="fn-proj-hero-stat">
          <div className="fn-stat-lbl">Owner</div>
          <div className="fn-proj-owner mono">{p.owner}</div>
          <div className="fn-stat-delta fn-muted">Created {p.created}</div>
        </div>
        <div className="fn-proj-hero-stat">
          <div className="fn-stat-lbl">Tags</div>
          <div className="fn-chips" style={{ marginTop: 6 }}>
            {Object.entries(p.tags).map(([k, v]) => (
              <span key={k} className="fn-chip fn-chip-sm">{k}: <b>{v}</b></span>
            ))}
          </div>
        </div>
      </div>

      <div className="fn-panel fn-panel-flush">
        <div className="fn-panel-head" style={{ padding: 'var(--s-4) var(--s-5)', margin: 0, borderBottom: '1px solid var(--border-subtle)' }}>
          <div><h3>Connections</h3><div className="fn-sub">{conns.length} in this project</div></div>
          <Button variant="outline" size="sm" icon="plus" onClick={() => onNewConnection(p.id)}>Add connection</Button>
        </div>
        <table className="fn-table">
          <thead><tr>
            <th>Name</th><th>Provider</th><th>Scope</th><th className="num">Resources</th><th>Status</th><th>Last run</th><th></th>
          </tr></thead>
          <tbody>
            {conns.map(c => (
              <tr key={c.id} className="is-clickable" onClick={() => onNav({ screen: 'connection', connectionId: c.id })}>
                <td className="mono fn-strong">{c.name}</td>
                <td><ProviderTag p={c.prov} /></td>
                <td className="fn-muted" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.scope}</td>
                <td className="num mono">{c.resources?.length || 0}</td>
                <td><Badge tone={c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err'} dot>{{ ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status]}</Badge></td>
                <td className="mono fn-muted">{c.lastRun}</td>
                <td style={{ width: 28 }}><Icon name="chevron-right" size={14} style={{ color: 'var(--fg-subtle)' }} /></td>
              </tr>
            ))}
            {conns.length === 0 && (
              <tr><td colSpan={7} className="fn-empty">
                No connections in this project.{' '}
                <button className="fn-linkbtn" onClick={() => onNewConnection(p.id)}>Add one →</button>
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="fn-panel">
        <div className="fn-panel-head"><h3>Notes</h3></div>
        <div className="fn-muted">{p.note}</div>
      </div>
    </div>
  );
}

// ============================================================================
// CONNECTION DETAIL (full page)
// ============================================================================
interface ConnectionDetailScreenProps {
  connectionId: string;
  onNav: (route: Route) => void;
  onNewResource: () => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onEditTags: (resource: Resource) => void;
  onMoveResource: (resource: Resource) => void;
}

export function ConnectionDetailScreen({ connectionId, onNav, onNewResource, pushToast, onEditTags, onMoveResource }: ConnectionDetailScreenProps) {
  const { CONNECTIONS, FIN_PROJECTS } = FINNA_DATA;
  const c = CONNECTIONS.find(x => x.id === connectionId);
  if (!c) return <div className="fn-screen"><TopBar title="Connection not found" /></div>;

  const project = FIN_PROJECTS.find(p => p.id === c.projectId);
  const tone = c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err';
  const label = { ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status];
  const totalCost = (c.resources || []).reduce((a, r) => a + r.mtd, 0);

  const [q, setQ] = useState('');
  const [sel, setSel] = useState<Set<string>>(new Set());

  const filtered = useMemo(
    () => (c.resources || []).filter(r =>
      q === '' || r.name.toLowerCase().includes(q.toLowerCase()) || r.type.toLowerCase().includes(q.toLowerCase())
    ),
    [q, c.resources]
  );

  const toggle = (id: string) => {
    const n = new Set(sel);
    if (n.has(id)) n.delete(id); else n.add(id);
    setSel(n);
  };

  return (
    <div className="fn-screen" data-screen-label={`Connection · ${c.name}`}>
      <TopBar
        breadcrumb={<Breadcrumb items={[
          { label: 'Connections', onClick: () => onNav({ screen: 'connections' }) },
          ...(project ? [{ label: project.name, onClick: () => onNav({ screen: 'project', projectId: project.id }) }] : []),
          { label: c.name },
        ]} />}
        title={<span className="mono">{c.name}</span>}
        subtitle={<><ProviderTag p={c.prov} /><span className="fn-muted" style={{ marginLeft: 8 }}>{c.scope}</span></>}
        actions={<>
          <Badge tone={tone} dot>{label}</Badge>
          <Button variant="outline" size="sm" icon="play"
            onClick={() => pushToast({ tone: 'ok', title: `Queued ${c.name}` })}>
            Run now
          </Button>
          <Button variant="outline" size="sm" icon="refresh-cw">Re-auth</Button>
          <Button variant="ghost" size="sm" icon="trash-2">Delete</Button>
        </>}
      />

      <div className="fn-conn-detail-grid">
        <div className="fn-panel">
          <div className="fn-panel-head"><h3>Details</h3></div>
          <div className="fn-kv-list">
            <div className="fn-kv"><span className="fn-k">Project</span><span className="fn-v">
              {project
                ? <button className="fn-linkbtn" onClick={() => onNav({ screen: 'project', projectId: project.id })}>{project.name}</button>
                : <span className="fn-muted">Unassigned</span>}
            </span></div>
            <div className="fn-kv"><span className="fn-k">Provider</span><span className="fn-v"><ProviderTag p={c.prov} /></span></div>
            <div className="fn-kv"><span className="fn-k">Auth method</span><span className="fn-v">{c.auth}</span></div>
            <div className="fn-kv"><span className="fn-k">Token</span><span className={`fn-v mono ${c.expires === 'expired' ? 'fn-up' : ''}`}>{c.expires}</span></div>
            <div className="fn-kv"><span className="fn-k">Last run</span><span className="fn-v mono">{c.lastRun}</span></div>
            <div className="fn-kv"><span className="fn-k">Rows last run</span><span className="fn-v mono">{c.rows || '—'}</span></div>
          </div>
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head"><h3>Scope & schedule</h3></div>
          <pre className="fn-code mono" style={{ marginBottom: 12 }}>{c.scope}</pre>
          <div className="fn-kv-list">
            <div className="fn-kv"><span className="fn-k">Cadence</span><span className="fn-v">Nightly · 02:00 UTC</span></div>
            <div className="fn-kv"><span className="fn-k">Next run</span><span className="fn-v mono">in 13h 42m</span></div>
            <div className="fn-kv"><span className="fn-k">Retention</span><span className="fn-v">12 months</span></div>
          </div>
          {c.err && <pre className="fn-code mono fn-code-err" style={{ marginTop: 12 }}>{c.err}</pre>}
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head"><h3>Cost snapshot</h3></div>
          <div className="fn-stat-val" style={{ fontSize: 'var(--fs-24)' }}>{fmt.money(totalCost)}</div>
          <div className="fn-stat-delta fn-muted">across {c.resources?.length || 0} resources · MTD</div>
          <hr />
          <div className="fn-kv"><span className="fn-k">Top resource</span><span className="fn-v mono">{c.resources?.[0]?.name || '—'}</span></div>
          <div className="fn-kv"><span className="fn-k">Resource types</span><span className="fn-v mono">{[...new Set((c.resources || []).map(r => r.type))].length}</span></div>
        </div>
      </div>

      <div className="fn-panel fn-panel-flush">
        <div className="fn-panel-head" style={{ padding: 'var(--s-4) var(--s-5)', margin: 0, borderBottom: '1px solid var(--border-subtle)' }}>
          <div>
            <h3>Resources</h3>
            <div className="fn-sub">{filtered.length} of {c.resources?.length || 0} shown{sel.size > 0 ? ` · ${sel.size} selected` : ''}</div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'center' }}>
            <div className="fn-inp-wrap" style={{ flex: '0 0 220px' }}>
              <Icon name="search" size={13} className="fn-inp-icon" />
              <input className="fn-inp" style={{ minWidth: 0, width: '100%', height: 30 }}
                placeholder="Filter resources…" value={q} onChange={e => setQ(e.target.value)} />
            </div>
            {sel.size > 0 && (
              <>
                <Button variant="outline" size="sm" icon="tag"
                  onClick={() => pushToast({ tone: 'info', title: `Tag ${sel.size} resources`, body: 'Tag dialog (mocked).' })}>
                  Tag
                </Button>
                <Button variant="outline" size="sm" icon="folder-input"
                  onClick={() => pushToast({ tone: 'info', title: `Move ${sel.size} resources`, body: 'Destination project picker (mocked).' })}>
                  Move
                </Button>
              </>
            )}
            <Button variant="primary" size="sm" icon="plus" onClick={onNewResource}>Add resource</Button>
          </div>
        </div>
        <table className="fn-table">
          <thead><tr>
            <th style={{ width: 32 }}></th>
            <th>Name</th><th>Type</th><th>Native ID</th><th>Tags</th><th className="num">MTD</th><th></th>
          </tr></thead>
          <tbody>
            {filtered.map(r => (
              <tr key={r.id} className="is-clickable">
                <td onClick={e => { e.stopPropagation(); toggle(r.id); }}>
                  <input type="checkbox" className="fn-check" checked={sel.has(r.id)}
                    onChange={() => toggle(r.id)} onClick={e => e.stopPropagation()} />
                </td>
                <td className="mono fn-strong" onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>{r.name}</td>
                <td onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>{r.type}</td>
                <td className="mono fn-muted" style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>{r.native}</td>
                <td onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>
                  <div className="fn-chips">
                    {Object.entries(r.tags).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="fn-chip fn-chip-sm">{k}:<b>{v}</b></span>
                    ))}
                  </div>
                </td>
                <td className="num mono fn-strong" onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>{fmt.money(r.mtd)}</td>
                <td onClick={() => onNav({ screen: 'resource', connectionId: c.id, resourceId: r.id })}>
                  <Icon name="chevron-right" size={14} style={{ color: 'var(--fg-subtle)' }} />
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={7} className="fn-empty">No resources match.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// RESOURCE DETAIL
// ============================================================================
interface ResourceDetailScreenProps {
  connectionId: string;
  resourceId: string;
  onNav: (route: Route) => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onEditTags: (resource: Resource) => void;
  onMoveResource: (resource: Resource) => void;
}

export function ResourceDetailScreen({ connectionId, resourceId, onNav, pushToast, onEditTags, onMoveResource }: ResourceDetailScreenProps) {
  const { CONNECTIONS, FIN_PROJECTS } = FINNA_DATA;
  const c = CONNECTIONS.find(x => x.id === connectionId);
  const r = c?.resources?.find(x => x.id === resourceId);
  if (!r || !c) return <div className="fn-screen"><TopBar title="Resource not found" /></div>;

  const project = FIN_PROJECTS.find(p => p.id === c.projectId);
  const daily = Array.from({ length: 14 }, (_, i) =>
    Math.max(0, r.mtd / 14 + Math.sin(i * 0.9) * r.mtd * 0.06 + (i === 9 ? r.mtd * 0.1 : 0))
  );

  return (
    <div className="fn-screen" data-screen-label={`Resource · ${r.name}`}>
      <TopBar
        breadcrumb={<Breadcrumb items={[
          { label: 'Connections', onClick: () => onNav({ screen: 'connections' }) },
          ...(project ? [{ label: project.name, onClick: () => onNav({ screen: 'project', projectId: project.id }) }] : []),
          { label: c.name, onClick: () => onNav({ screen: 'connection', connectionId: c.id }) },
          { label: r.name },
        ]} />}
        title={<span className="mono">{r.name}</span>}
        subtitle={<>{r.type} · <span className="mono fn-muted">{r.native}</span></>}
        actions={<>
          <Button variant="outline" size="sm" icon="tag" onClick={() => onEditTags(r)}>Edit tags</Button>
          <Button variant="outline" size="sm" icon="folder-input" onClick={() => onMoveResource(r)}>Move to project</Button>
          <Button variant="ghost" size="sm" icon="trash-2">Delete</Button>
        </>}
      />

      <div className="fn-stats-row" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
        <StatCard label="MTD · USD" value={fmt.money(r.mtd)} meta="14-day window" />
        <StatCard label="Daily avg" value={fmt.money(r.mtd / 14)} meta="USD / day" />
        <StatCard label="Type" value={r.type} meta={c.prov.toUpperCase()} />
      </div>

      <div className="fn-conn-detail-grid">
        <div className="fn-panel">
          <div className="fn-panel-head"><h3>Identity</h3></div>
          <div className="fn-kv-list">
            <div className="fn-kv"><span className="fn-k">Name</span><span className="fn-v mono">{r.name}</span></div>
            <div className="fn-kv"><span className="fn-k">Resource ID</span><span className="fn-v mono">{r.id}</span></div>
            <div className="fn-kv"><span className="fn-k">Provider ID</span><span className="fn-v mono" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.native}>{r.native}</span></div>
            <div className="fn-kv"><span className="fn-k">Type</span><span className="fn-v">{r.type}</span></div>
          </div>
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head">
            <h3>Tags</h3>
            <Button variant="ghost" size="xs" icon="pencil" onClick={() => onEditTags(r)}>Edit</Button>
          </div>
          <div className="fn-chips" style={{ gap: 6 }}>
            {Object.entries(r.tags).map(([k, v]) => (
              <span key={k} className="fn-chip">{k}: <b>{v}</b></span>
            ))}
            {Object.keys(r.tags).length === 0 && <span className="fn-muted">No tags yet.</span>}
          </div>
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head"><h3>Location</h3></div>
          <div className="fn-kv-list">
            <div className="fn-kv"><span className="fn-k">Connection</span><span className="fn-v">
              <button className="fn-linkbtn mono" onClick={() => onNav({ screen: 'connection', connectionId: c.id })}>{c.name}</button>
            </span></div>
            <div className="fn-kv"><span className="fn-k">Project</span><span className="fn-v">
              {project
                ? <button className="fn-linkbtn" onClick={() => onNav({ screen: 'project', projectId: project.id })}>{project.name}</button>
                : <span className="fn-muted">Unassigned</span>}
            </span></div>
            <div className="fn-kv"><span className="fn-k">Provider</span><span className="fn-v"><ProviderTag p={c.prov} /></span></div>
          </div>
        </div>
      </div>

      <div className="fn-panel">
        <div className="fn-panel-head"><h3>Daily spend · 14d</h3></div>
        <MiniBars data={daily} />
      </div>
    </div>
  );
}
