import React from 'react';
import type { CostRecord } from '../../types';

interface CostDrawerProps {
  row: CostRecord | null;
  onClose: () => void;
}

export function CostDrawer({ row, onClose }: CostDrawerProps) {
  if (!row) return null;

  return (
    <>
      <div className="fn-drawer-scrim is-open" onClick={onClose} />
      <aside className="fn-drawer is-open">
        <div className="fn-drawer-head">
          <div>
            <div className="fn-drawer-title">Cost details</div>
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="fn-drawer-body">
          <p>Cost drawer implementation in progress...</p>
        </div>
      </aside>
    </>
  );
}
