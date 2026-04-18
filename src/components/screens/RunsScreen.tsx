import React, { useState } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { Skeleton } from '../common/Skeleton';
import { ErrorMessage } from '../common/ErrorMessage';
import { useExtractorRuns } from '../../api/queries';
import type { Run } from '../../types';

interface RunsScreenProps {
  onOpenRun: (run: Run) => void;
}

export function RunsScreen({ onOpenRun }: RunsScreenProps) {
  const { data: runsData, loading, error, refetch } = useExtractorRuns();
  const [flt, setFlt] = useState<'all' | 'success' | 'running' | 'failed'>('all');

  const RUNS: Run[] = runsData
    ? runsData.map(r => ({
        id: r.id,
        type: r.extractor_type,
        prov: (r.provider || 'ecb') as any,
        status: r.status === 'running' ? 'running' : r.status === 'success' ? 'success' : 'failed',
        started: r.started_at,
        dur: r.finished_at && r.started_at
          ? (() => { const d = new Date(r.finished_at).getTime() - new Date(r.started_at).getTime(); return d < 60000 ? `${Math.round(d/1000)}s` : `${Math.floor(d/60000)}m ${Math.round((d%60000)/1000)}s`; })()
          : '—',
        rows: r.records_extracted,
        err: r.error_message || undefined,
      }))
    : [];

  const rows = flt === 'all' ? RUNS : RUNS.filter(r => r.status === flt);

  if (loading) {
    return (
      <div className="fn-screen" data-screen-label="Run log">
        <TopBar title="Run log" subtitle="Loading..." />
        <div style={{ padding: 24 }}><Skeleton height={40} /><Skeleton height={40} /><Skeleton height={40} /></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fn-screen" data-screen-label="Run log">
        <TopBar title="Run log" subtitle="Error" />
        <ErrorMessage message={`Failed to load runs: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="fn-screen" data-screen-label="Run log">
      <TopBar title="Run log"
        subtitle={`Last ${RUNS.length} subprocess runs · from extractor_runs`}
        actions={<Button variant="outline" size="sm" icon="refresh-cw" onClick={refetch}>Refresh</Button>}
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
            {rows.length === 0 && <tr><td colSpan={8} className="fn-empty">No runs found.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
