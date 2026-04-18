import React from 'react';
import type { Toast, CostRecord } from '../../types';

interface ExplorerScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onOpenCost: (cost: CostRecord) => void;
}

export function ExplorerScreen({ pushToast, onOpenCost }: ExplorerScreenProps) {
  return (
    <div className="fn-screen" data-screen-label="Explorer">
      <header className="fn-topbar">
        <div className="fn-topbar-l">
          <div className="fn-topbar-title">Cost explorer</div>
        </div>
      </header>
      <div style={{ padding: 'var(--s-7)' }}>
        <p>Explorer implementation in progress...</p>
      </div>
    </div>
  );
}
