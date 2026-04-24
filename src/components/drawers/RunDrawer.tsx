import React from 'react';
import type { Run } from '../../types';

interface RunDrawerProps {
  run: Run | null;
  onClose: () => void;
}

export function RunDrawer({ run, onClose }: RunDrawerProps) {
  if (!run) return null;

  return (
    <>
      <div className="fn-drawer-scrim is-open" onClick={onClose} />
      <aside className="fn-drawer is-open">
        <div className="fn-drawer-head">
          <div>
            <div className="fn-drawer-title">Run details</div>
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="fn-drawer-body">
          <p>Run drawer implementation in progress...</p>
        </div>
      </aside>
    </>
  );
}
