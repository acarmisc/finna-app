import React, { useState, useMemo } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { Breadcrumb } from '../common/Breadcrumb';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { Toast, Route } from '../../types';

interface ConnectionDetailScreenProps {
  connectionId: string;
  onNav: (route: Route) => void;
  onOpenResource: (connId: string, resId: string) => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onNewResource: () => void;
}

export function ConnectionDetailScreen({
  connectionId, onNav, onOpenResource, pushToast, onNewResource,
}: ConnectionDetailScreenProps) {
  const { CONNECTIONS, FIN_PROJECTS } = FINNA_DATA;
  const c = CONNECTIONS.find(x => x.id === connectionId);
  if (!c) return <div className="fn-screen"><TopBar title="Connection not found" /></div>;

  const project = FIN_PROJECTS.find(p => p.id === c.projectId);
  const tone = c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err';
  const statusLabel = { ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status];
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
          <Badge tone={tone} dot>{statusLabel}</Badge>
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
            <div className="fn-kv">
              <span className="fn-k">Project</span>
              <span className="fn-v">
                {project
                  ? <button className="fn-linkbtn" onClick={() => onNav({ screen: 'project', projectId: project.id })}>{project.name}</button>
                  : <span className="fn-muted">Unassigned</span>}
              </span>
            </div>
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
                  onClick={() => pushToast({ tone: 'info', title: `Tag ${sel.size} resources` })}>Tag</Button>
                <Button variant="outline" size="sm" icon="folder-input"
                  onClick={() => pushToast({ tone: 'info', title: `Move ${sel.size} resources` })}>Move</Button>
              </>
            )}
            <Button variant="primary" size="sm" icon="plus" onClick={onNewResource}>Add resource</Button>
          </div>
        </div>
        <table className="fn-table">
          <thead><tr>
            <th style={{ width: 32 }}></th>
            <th>Name</th><th>Type</th><th>Native ID</th><th>Tags</th>
            <th className="num">MTD</th><th></th>
          </tr></thead>
          <tbody>
            {filtered.map(r => (
              <tr key={r.id} className="is-clickable">
                <td onClick={e => { e.stopPropagation(); toggle(r.id); }}>
                  <input type="checkbox" className="fn-check" checked={sel.has(r.id)}
                    onChange={() => toggle(r.id)} onClick={e => e.stopPropagation()} />
                </td>
                <td className="mono fn-strong" onClick={() => onOpenResource(c.id, r.id)}>{r.name}</td>
                <td onClick={() => onOpenResource(c.id, r.id)}>{r.type}</td>
                <td className="mono fn-muted" style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  onClick={() => onOpenResource(c.id, r.id)}>{r.native}</td>
                <td onClick={() => onOpenResource(c.id, r.id)}>
                  <div className="fn-chips">
                    {Object.entries(r.tags).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="fn-chip fn-chip-sm">{k}:<b>{v}</b></span>
                    ))}
                  </div>
                </td>
                <td className="num mono fn-strong" onClick={() => onOpenResource(c.id, r.id)}>{fmt.money(r.mtd)}</td>
                <td onClick={() => onOpenResource(c.id, r.id)}>
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
