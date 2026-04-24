import React from 'react';
import type { Toast, Connection } from '../../types';

interface ConnectionsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onNew: () => void;
  onOpen: (conn: Connection) => void;
}

export function ConnectionsScreen({ pushToast, onNew, onOpen }: ConnectionsScreenProps) {
  return (
    <div className="fn-screen" data-screen-label="Connections">
      <header className="fn-topbar">
        <div className="fn-topbar-l">
          <div className="fn-topbar-title">Connections</div>
        </div>
      </header>
      <div style={{ padding: 'var(--s-7)' }}>
        <p>Connections implementation in progress...</p>
      </div>
    </div>
  );
}
