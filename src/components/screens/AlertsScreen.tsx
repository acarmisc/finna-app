import React from 'react';
import type { Toast } from '../../types';

interface AlertsScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function AlertsScreen({ pushToast }: AlertsScreenProps) {
  return (
    <div className="fn-screen" data-screen-label="Alerts">
      <header className="fn-topbar">
        <div className="fn-topbar-l">
          <div className="fn-topbar-title">Alerts</div>
        </div>
      </header>
      <div style={{ padding: 'var(--s-7)' }}>
        <p>Alerts implementation in progress...</p>
      </div>
    </div>
  );
}
