import React from 'react';
import type { Connection } from '../../types';

interface NewConnectionModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (conn: Connection) => void;
}

export function NewConnectionModal({ open, onClose, onCreate }: NewConnectionModalProps) {
  if (!open) return null;

  return (
    <div className="fn-scrim" onClick={onClose}>
      <div className="fn-modal" onClick={e => e.stopPropagation()}>
        <div className="fn-modal-head">
          <div>
            <div className="fn-modal-title">New connection</div>
            <div className="fn-modal-sub">Add a new cloud provider connection</div>
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="fn-modal-body">
          <p>Modal implementation in progress...</p>
        </div>
        <div className="fn-modal-foot">
          <button onClick={onClose}>Cancel</button>
          <button onClick={onClose}>Create</button>
        </div>
      </div>
    </div>
  );
}
