import React from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { StatCard } from '../common/StatCard';
import { ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { Breadcrumb } from '../common/Breadcrumb';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { Toast, Route } from '../../types';

interface ResourceDetailScreenProps {
  connectionId: string;
  resourceId: string;
  onNav: (route: Route) => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onEditTags: () => void;
  onMoveResource: () => void;
}

export function ResourceDetailScreen({
  connectionId, resourceId, onNav, pushToast, onEditTags, onMoveResource,
}: ResourceDetailScreenProps) {
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
          <Button variant="outline" size="sm" icon="tag" onClick={onEditTags}>Edit tags</Button>
          <Button variant="outline" size="sm" icon="folder-input" onClick={onMoveResource}>Move to project</Button>
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
            <div className="fn-kv">
              <span className="fn-k">Provider ID</span>
              <span className="fn-v mono" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.native}>{r.native}</span>
            </div>
            <div className="fn-kv"><span className="fn-k">Type</span><span className="fn-v">{r.type}</span></div>
          </div>
        </div>
        <div className="fn-panel">
          <div className="fn-panel-head">
            <h3>Tags</h3>
            <Button variant="ghost" size="xs" icon="pencil" onClick={onEditTags}>Edit</Button>
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
            <div className="fn-kv">
              <span className="fn-k">Connection</span>
              <span className="fn-v">
                <button className="fn-linkbtn mono" onClick={() => onNav({ screen: 'connection', connectionId: c.id })}>{c.name}</button>
              </span>
            </div>
            <div className="fn-kv">
              <span className="fn-k">Project</span>
              <span className="fn-v">
                {project
                  ? <button className="fn-linkbtn" onClick={() => onNav({ screen: 'project', projectId: project.id })}>{project.name}</button>
                  : <span className="fn-muted">Unassigned</span>}
              </span>
            </div>
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

function MiniBars({ data }: { data: number[] }) {
  const max = Math.max(...data) || 1;
  return (
    <div className="fn-minibars">
      {data.map((v, i) => (
        <div key={i} className="fn-minibar-col">
          <div className="fn-minibar-fill" style={{ height: (v / max * 100) + '%' }} />
          <div className="fn-minibar-lbl">{i + 1}</div>
        </div>
      ))}
    </div>
  );
}
