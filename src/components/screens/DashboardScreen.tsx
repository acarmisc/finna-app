import React from 'react';
import type { Toast } from '../../types';

interface DashboardScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
}

export function DashboardScreen({ pushToast }: DashboardScreenProps) {
  return (
    <div className="fn-screen" data-screen-label="Dashboard">
      <header className="fn-topbar">
        <div className="fn-topbar-l">
          <div className="fn-topbar-title">Overview</div>
          <div className="fn-topbar-sub">Dashboard screen (coming soon)</div>
        </div>
      </header>
      <div style={{ padding: 'var(--s-7)' }}>
        <p>Dashboard implementation in progress...</p>
      </div>
    </div>
  );
}
