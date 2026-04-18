import React from 'react';
import { Drawer } from '../common/Drawer';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { ProviderTag } from '../common/ProviderTag';
import type { Connection, Toast } from '../../types';

interface ConnectionDrawerProps {
  c: Connection | null;
  onClose: () => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function ConnectionDrawer({ c, onClose, pushToast }: ConnectionDrawerProps) {
  if (!c) return null;
  const tone = c.status === 'ok' ? 'ok' : c.status === 'warn' ? 'warn' : 'err';
  return (
    <Drawer
      open={!!c}
      onClose={onClose}
      title={<span className="mono">{c.name}</span>}
      subtitle={<ProviderTag p={c.prov} />}
      width={520}
      footer={<>
        <Button variant="outline" size="sm" icon="play"
          onClick={() => pushToast({ tone: 'ok', title: `Queued ${c.name}` })}>
          Run now
        </Button>
        <Button variant="ghost" size="sm" icon="refresh-cw">Re-authenticate</Button>
        <Button variant="ghost" size="sm" icon="trash-2">Delete</Button>
      </>}
    >
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Status</div>
        <div className="fn-kv"><span className="fn-k">Health</span><span className="fn-v"><Badge tone={tone} dot>{{ ok: 'Healthy', warn: 'Stale', err: 'Failed' }[c.status]}</Badge></span></div>
        <div className="fn-kv"><span className="fn-k">Last run</span><span className="fn-v mono">{c.lastRun}</span></div>
        <div className="fn-kv"><span className="fn-k">Rows (last run)</span><span className="fn-v mono">{c.rows || '—'}</span></div>
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Authentication</div>
        <div className="fn-kv"><span className="fn-k">Method</span><span className="fn-v">{c.auth}</span></div>
        <div className="fn-kv"><span className="fn-k">Token expires</span><span className={`fn-v mono ${c.expires === 'expired' ? 'fn-up' : ''}`}>{c.expires}</span></div>
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Scope</div>
        <pre className="fn-code mono">{c.scope}</pre>
      </div>
      {c.err && (
        <div className="fn-drawer-section">
          <div className="fn-sec-lbl">Last error</div>
          <pre className="fn-code mono fn-code-err">{c.err}</pre>
        </div>
      )}
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Schedule</div>
        <div className="fn-kv"><span className="fn-k">Cadence</span><span className="fn-v">Nightly · 02:00 UTC</span></div>
        <div className="fn-kv"><span className="fn-k">Next run</span><span className="fn-v mono">in 13h 42m</span></div>
        <div className="fn-kv"><span className="fn-k">Retention</span><span className="fn-v">12 months</span></div>
      </div>
    </Drawer>
  );
}
