import React, { useState } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag, ProviderDot } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';
import type { Toast, Connection, Route } from '../../types';

interface ConnectionsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onNew: () => void;
  onOpen: (conn: Connection) => void;
  onNav: (route: Route) => void;
}

export function ConnectionsScreen({ pushToast, onNew, onOpen, onNav }: ConnectionsScreenProps) {
  const { CONNECTIONS, FIN_PROJECTS } = FINNA_DATA;
  const [view, setView] = useState<'cards' | 'table'>(
    (localStorage.getItem('finna-conn-view') as 'cards' | 'table') || 'cards'
  );

  const projectFor = (pid?: string | null) => FIN_PROJECTS.find(p => p.id === pid);

  const handleViewChange = (v: 'cards' | 'table') => {
    setView(v);
    localStorage.setItem('finna-conn-view', v);
  };

  return (
    <div className="fn-screen" data-screen-label="Connections">
      <TopBar title="Connections"
        subtitle={`${CONNECTIONS.length} active · 1 failing · 2 OAuth tokens expiring in 7d`}
        actions={<>
          <div className="fn-seg">
            {([['cards', 'Cards'], ['table', 'Table']] as const).map(([k, l]) => (
              <button key={k} className={`fn-seg-btn ${view === k ? 'is-active' : ''}`} onClick={() => handleViewChange(k)}>{l}</button>
            ))}
          </div>
          <Button variant="outline" size="sm" icon="refresh-cw"
            onClick={() => pushToast({ tone: 'info', title: 'Re-checking all connections' })}>
            Check all
          </Button>
          <Button variant="primary" size="sm" icon="plus" onClick={onNew}>New connection</Button>
        </>}
      />
      {view === 'cards' ? (
        <div className="fn-conn-grid">
          {CONNECTIONS.map(c => (
            <ConnectionCard key={c.id} c={c} project={projectFor(c.projectId)}
              onClick={() => onOpen(c)}
              onRun={() => pushToast({ tone: 'ok', title: `Queued ${c.name}`, body: 'Run will start in ~5s' })}
              onOpenProject={onNav}
            />
          ))}
        </div>
      ) : (
        <div className="fn-panel fn-panel-flush">
          <table className="fn-table">
            <thead><tr>
              <th>Name</th><th>Provider</th><th>Project</th><th>Scope</th>
              <th className="num">Resources</th><th>Status</th><th>Last run</th><th></th>
            </tr></thead>
            <tbody>
              {CONNECTIONS.map(c => {
                const p = projectFor(c.projectId);
                return (
                  <tr key={c.id} className="is-clickable" onClick={() => onOpen(c)}>
                    <td className="mono fn-strong">{c.name}</td>
                    <td><ProviderTag p={c.prov} /></td>
                    <td>
                      {p
                        ? <button className="fn-linkbtn" onClick={e => { e.stopPropagation(); onNav({ screen: 'project', projectId: p.id }); }}>{p.name}</button>
                        : <span className="fn-muted">Unassigned</span>}
                    </td>
                    <td className="fn-muted" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.scope}</td>
                    <td className="num mono">{c.resources?.length || 0}</td>
                    <td><Badge tone={c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err'} dot>{{ ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status]}</Badge></td>
                    <td className="mono fn-muted">{c.lastRun}</td>
                    <td><Icon name="chevron-right" size={14} style={{ color: 'var(--fg-subtle)' }} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function ConnectionCard({ c, project, onClick, onRun, onOpenProject }: {
  c: Connection;
  project?: ReturnType<typeof FINNA_DATA.FIN_PROJECTS.find>;
  onClick: () => void;
  onRun: () => void;
  onOpenProject: (route: Route) => void;
}) {
  const tone = c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err';
  const label = { ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status];
  return (
    <div className="fn-panel fn-conn is-clickable" onClick={onClick}>
      <div className="fn-conn-head">
        <div className="fn-conn-title">
          <ProviderDot p={c.prov} />
          <span className="mono">{c.name}</span>
        </div>
        <Badge tone={tone} dot>{label}</Badge>
      </div>
      <div className="fn-conn-project">
        {project ? (
          <button className="fn-linkbtn" onClick={e => { e.stopPropagation(); onOpenProject({ screen: 'project', projectId: project.id }); }}>
            <Icon name="folder" size={11} /> {project.name}
          </button>
        ) : <span className="fn-muted"><Icon name="folder-x" size={11} /> Unassigned</span>}
      </div>
      <div className="fn-conn-scope">{c.scope}</div>
      <div className="fn-conn-grid-meta">
        <div><span className="fn-k">Last run</span><span className="fn-v mono">{c.lastRun}</span></div>
        <div><span className="fn-k">Rows</span><span className="fn-v mono">{c.rows || '—'}</span></div>
        <div><span className="fn-k">Auth</span><span className="fn-v">{c.auth}</span></div>
        <div><span className="fn-k">Token</span><span className="fn-v">{c.expires}</span></div>
      </div>
      {c.err && <div className="fn-conn-err mono">{c.err}</div>}
      {c.note && <div className="fn-conn-note">{c.note}</div>}
      <div className="fn-conn-foot" onClick={e => e.stopPropagation()}>
        <Button variant="outline" size="sm" icon="play" onClick={onRun}>Run now</Button>
        <Button variant="ghost" size="sm" icon="settings" onClick={onClick}>Configure</Button>
        <Button variant="ghost" size="sm" icon="external-link">Logs</Button>
      </div>
    </div>
  );
}
