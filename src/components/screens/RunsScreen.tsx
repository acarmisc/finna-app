import React, { useState } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';
import type { Run } from '../../types';

interface RunsScreenProps {
  onOpenRun: (run: Run) => void;
}

export function RunsScreen({ onOpenRun }: RunsScreenProps) {
  const { RUNS } = FINNA_DATA;
  const [flt, setFlt] = useState<'all' | 'success' | 'running' | 'failed'>('all');
  const rows = flt === 'all' ? RUNS : RUNS.filter(r => r.status === flt);

  return (
    <div className="fn-screen" data-screen-label="Run log">
      <TopBar title="Run log"
        subtitle={`Last ${RUNS.length} subprocess runs · from extractor_runs`}
        actions={<Button variant="outline" size="sm" icon="refresh-cw">Refresh</Button>}
      />
      <div className="fn-filter-bar">
        <div className="fn-seg">
          {([['all', 'All'], ['success', 'Success'], ['running', 'Running'], ['failed', 'Failed']] as [typeof flt, string][]).map(([k, l]) => (
            <button key={k} className={`fn-seg-btn ${flt === k ? 'is-active' : ''}`} onClick={() => setFlt(k)}>{l}</button>
          ))}
        </div>
        <div className="fn-chips"><span className="fn-chip">Window: <b>Last 24h</b></span></div>
      </div>
      <div className="fn-panel fn-panel-flush">
        <table className="fn-table">
          <thead><tr>
            <th>Status</th><th>Run ID</th><th>Extractor</th><th>Provider</th>
            <th>Started</th><th>Duration</th><th className="num">Rows</th><th></th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="is-clickable" onClick={() => onOpenRun(r)}>
                <td><Badge tone={r.status === 'success' ? 'ok' : r.status === 'running' ? 'info' : 'err'} dot>{r.status}</Badge></td>
                <td className="mono fn-muted">{r.id}</td>
                <td className="mono">{r.type}</td>
                <td><ProviderTag p={r.prov} /></td>
                <td>{r.started}</td>
                <td className="mono">{r.dur}</td>
                <td className="num mono">{r.rows.toLocaleString()}</td>
                <td><Icon name="chevron-right" size={14} style={{ color: 'var(--fg-subtle)' }} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
