import React from 'react';
import type { Connection, Toast } from '../../types';

interface ConnectionDrawerProps {
  c: Connection | null;
  onClose: () => void;
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function ConnectionDrawer({ c, onClose, pushToast }: ConnectionDrawerProps) {
  if (!c) return null;

  return (
    <>
      <div className="fn-drawer-scrim is-open" onClick={onClose} />
      <aside className="fn-drawer is-open">
        <div className="fn-drawer-head">
          <div>
            <div className="fn-drawer-title">Connection details</div>
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="fn-drawer-body">
          <p>Drawer implementation in progress...</p>
        </div>
      </aside>
    </>
  );
}
