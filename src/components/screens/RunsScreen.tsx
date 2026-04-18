import React from 'react';
import type { Run } from '../../types';

interface RunsScreenProps {
  onOpenRun: (run: Run) => void;
}

export function RunsScreen({ onOpenRun }: RunsScreenProps) {
  return (
    <div className="fn-screen" data-screen-label="Runs">
      <header className="fn-topbar">
        <div className="fn-topbar-l">
          <div className="fn-topbar-title">Run log</div>
        </div>
      </header>
      <div style={{ padding: 'var(--s-7)' }}>
        <p>Run log implementation in progress...</p>
      </div>
    </div>
  );
}
