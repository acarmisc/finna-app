import React from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderDot, ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { Breadcrumb } from '../common/Breadcrumb';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { Toast, Route } from '../../types';

interface ProjectsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onOpenProject: (id: string) => void;
  onNewProject: () => void;
}

export function ProjectsScreen({ pushToast, onOpenProject, onNewProject }: ProjectsScreenProps) {
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
            <div key={p.id} className="fn-panel fn-proj is-clickable" onClick={() => onOpenProject(p.id)}>
              <div className="fn-proj-head">
                <div>
                  <div className="fn-proj-name">{p.name}</div>
                  <div className="fn-proj-slug mono">{p.slug} · {p.costCenter}</div>
                </div>
                <Badge tone={over ? 'err' : 'ok'} dot>{over ? 'Over 80%' : 'Healthy'}</Badge>
              </div>
              <div className="fn-proj-budget">
                <div className="fn-budget-bar">
                  <div className="fn-budget-fill" style={{
                    width: Math.min(pct, 1) * 100 + '%',
                    background: over ? 'var(--danger)' : 'var(--primary)',
                  }} />
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
              <div className="fn-sub">Not bound to any project. Move them in for budget governance.</div>
            </div>
          </div>
          <div className="fn-unassigned">
            {unassignedConns.map(c => (
              <div key={c.id} className="fn-unassigned-row">
                <ProviderDot p={c.prov} />
                <span className="mono fn-strong">{c.name}</span>
                <span className="fn-muted">{c.scope}</span>
                <Button variant="outline" size="xs" icon="folder-plus"
                  onClick={() => pushToast({ tone: 'info', title: 'Move connection', body: 'Select a project in the dialog.' })}>
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

interface ProjectDetailScreenProps {
  projectId: string;
  onNav: (route: Route) => void;
  onOpenConnection: (id: string) => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onNewConnection: (pid: string) => void;
}

export function ProjectDetailScreen({ projectId, onNav, onOpenConnection, pushToast, onNewConnection }: ProjectDetailScreenProps) {
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
            onClick={() => pushToast({ tone: 'info', title: 'Edit tags', body: 'Tag editor opened.' })}>
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
            <th>Name</th><th>Provider</th><th>Scope</th><th className="num">Resources</th>
            <th>Status</th><th>Last run</th><th></th>
          </tr></thead>
          <tbody>
            {conns.map(c => (
              <tr key={c.id} className="is-clickable" onClick={() => onOpenConnection(c.id)}>
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
