import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { ProviderDot } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';
import type { Resource } from '../../types';

interface MoveResourceModalProps {
  open: boolean;
  onClose: () => void;
  resource: Resource | null;
  currentConnectionId: string | null;
  onMove: (destConnId: string) => void;
}

export function MoveResourceModal({ open, onClose, resource, currentConnectionId, onMove }: MoveResourceModalProps) {
  const { CONNECTIONS, FIN_PROJECTS } = FINNA_DATA;
  const [destConn, setDestConn] = useState('');

  useEffect(() => { if (open) setDestConn(''); }, [open]);

  if (!resource) return null;

  return (
    <Modal open={open} onClose={onClose}
      title="Move resource"
      subtitle={<>Move <span className="mono">{resource.name}</span> to another connection / project.</>}
      width={520}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="primary" icon="check" disabled={!destConn} onClick={() => { onMove(destConn); onClose(); }}>
          Move resource
        </Button>
      </>}
    >
      <div className="fn-choice-col">
        {CONNECTIONS.filter(c => c.id !== currentConnectionId).map(c => {
          const project = FIN_PROJECTS.find(p => p.id === c.projectId);
          return (
            <button key={c.id} className={`fn-choice ${destConn === c.id ? 'is-active' : ''}`}
              onClick={() => setDestConn(c.id)}>
              <ProviderDot p={c.prov} />
              <div>
                <div className="fn-choice-t mono">{c.name}</div>
                <div className="fn-choice-s">{project ? `${project.name} · ` : 'Unassigned · '}{c.scope}</div>
              </div>
              {destConn === c.id && <Icon name="check" size={14} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
            </button>
          );
        })}
      </div>
    </Modal>
  );
}
