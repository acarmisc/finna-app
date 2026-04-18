import React from 'react';
import { Drawer } from '../common/Drawer';
import { Button } from '../common/Button';
import { ProviderTag } from '../common/ProviderTag';
import { MiniBars } from '../common/MiniBars';
import { fmt } from '../../utils/fmt';
import type { CostRecord } from '../../types';

interface CostDrawerProps {
  row: CostRecord | null;
  onClose: () => void;
}

export function CostDrawer({ row, onClose }: CostDrawerProps) {
  if (!row) return null;
  const daily = Array.from({ length: 14 }, (_, i) =>
    Math.max(0, row.mtd / 14 + (Math.sin(i * 0.9) * row.mtd * 0.06) + (i === 9 ? row.mtd * 0.1 : 0))
  );

  return (
    <Drawer
      open={!!row}
      onClose={onClose}
      title={<><span className="mono">{row.name}</span> <span className="fn-muted"> · {row.sku}</span></>}
      subtitle={<ProviderTag p={row.prov} />}
      width={560}
      footer={<>
        <Button variant="outline" size="sm" icon="chart-line">Open in Explorer</Button>
        <Button variant="ghost" size="sm" icon="bell-plus">Create alert</Button>
      </>}
    >
      <div className="fn-drawer-stats">
        <div className="fn-mini-stat"><div className="fn-stat-lbl">MTD · USD</div><div className="fn-stat-val">{fmt.money(row.mtd)}</div></div>
        <div className="fn-mini-stat"><div className="fn-stat-lbl">Prev month</div><div className="fn-stat-val fn-muted">{fmt.money(row.prev)}</div></div>
        <div className="fn-mini-stat"><div className="fn-stat-lbl">Δ vs prev</div><div className={`fn-stat-val fn-${row.delta > 0 ? 'up' : 'down'}`}>{fmt.pct(row.delta)}</div></div>
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Daily trend · 14d</div>
        <MiniBars data={daily} />
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Source</div>
        <pre className="fn-code mono">{`SELECT day, sum(cost_usd)\nFROM cost_records\nWHERE provider = '${row.prov}'\n  AND project  = '${row.name}'\n  AND sku      = '${row.sku}'\nGROUP BY day ORDER BY day;`}</pre>
      </div>
      <div className="fn-drawer-section">
        <div className="fn-sec-lbl">Tags</div>
        <div className="fn-chips">
          <span className="fn-chip">env: <b>prod</b></span>
          <span className="fn-chip">team: <b>platform</b></span>
          <span className="fn-chip">cost_center: <b>eng-001</b></span>
        </div>
      </div>
    </Drawer>
  );
}
