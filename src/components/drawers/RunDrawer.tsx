import React from 'react';
import { Drawer } from '../common/Drawer';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { ProviderTag } from '../common/ProviderTag';
import type { Run } from '../../types';

interface RunDrawerProps {
  run: Run | null;
  onClose: () => void;
}

export function RunDrawer({ run, onClose }: RunDrawerProps) {
  if (!run) return null;

  const logs = run.status === 'failed' ? [
    { text: `[${run.started}] starting extractor=${run.type} prov=${run.prov}`, tone: '' },
    { text: `[${run.started}] resolving credentials from OS keyring…`, tone: '' },
    { text: `[${run.started}] fetching access token for Azure Cost Management API`, tone: '' },
    { text: `ERROR  AADSTS700082: The refresh token has expired due to inactivity.`, tone: 'fn-log-err' },
    { text: `ERROR  extractor exited with code 1 after ${run.dur}`, tone: 'fn-log-err' },
  ] : run.status === 'running' ? [
    { text: `[${run.started}] starting extractor=${run.type}`, tone: '' },
    { text: `[${run.started}] OTLP gRPC connection established`, tone: '' },
    { text: `INFO  polling spans… batch 1/?`, tone: 'fn-log-info' },
  ] : [
    { text: `[${run.started}] starting extractor=${run.type} prov=${run.prov}`, tone: '' },
    { text: `[${run.started}] credentials resolved (method=service_principal)`, tone: '' },
    { text: `[${run.started}] fetched ${run.rows.toLocaleString()} rows`, tone: '' },
    { text: `[${run.started}] normalized to cost_records schema`, tone: '' },
    { text: `[${run.started}] upserted ${run.rows.toLocaleString()} rows into cost_records (partition=2025_11)`, tone: '' },
    { text: `[${run.started}] completed in ${run.dur}`, tone: '' },
  ];

  const statusTone = run.status === 'success' ? 'ok' : run.status === 'running' ? 'info' : 'err';

  return (
    <Drawer
      open={!!run}
      onClose={onClose}
      title={<span className="mono">{run.id}</span>}
      subtitle={<><Badge tone={statusTone} dot>{run.status}</Badge><span className="mono" style={{ marginLeft: 8 }}>{run.type}</span></>}
      width={600}
      footer={<>
        {run.status === 'failed' && <Button variant="primary" size="sm" icon="refresh-cw">Retry</Button>}
        <Button variant="outline" size="sm" icon="download">Download log</Button>
      </>}
    >
      <div className="fn-drawer-stats">
        <div className="fn-mini-stat"><div className="fn-stat-lbl">Duration</div><div className="fn-stat-val">{run.dur}</div></div>
        <div className="fn-mini-stat"><div className="fn-stat-lbl">Rows</div><div className="fn-stat-val">{run.rows.toLocaleString()}</div></div>
        <div className="fn-mini-stat"><div className="fn-stat-lbl">Provider</div><div className="fn-stat-val"><ProviderTag p={run.prov} /></div></div>
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Subprocess output</div>
        <pre className="fn-logs mono">
          {logs.map((l, i) => (
            <div key={i} className={`fn-log-line ${l.tone}`}>{l.text}</div>
          ))}
        </pre>
      </div>
    </Drawer>
  );
}
