import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { FINNA_DATA } from '../../data';
import type { Connection, Resource } from '../../types';

interface NewResourceModalProps {
  open: boolean;
  onClose: () => void;
  connection: Connection | null;
  onCreate: (r: Resource) => void;
}

const TYPE_OPTIONS: Record<string, string[]> = {
  azure: ['Virtual Machine', 'Storage Account', 'Synapse Pool', 'App Service', 'PostgreSQL', 'Log Workspace'],
  gcp: ['Compute Engine', 'Cloud Storage', 'BQ Dataset', 'Vertex Endpoint', 'GKE Cluster'],
  llm: ['LLM Model'],
  aws: ['EC2 Instance', 'S3 Bucket', 'RDS'],
};

export function NewResourceModal({ open, onClose, connection, onCreate }: NewResourceModalProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [native, setNative] = useState('');
  const [tags, setTags] = useState<Record<string, string>>({});
  const { TAG_VOCAB } = FINNA_DATA;

  useEffect(() => {
    if (open) { setName(''); setType(''); setNative(''); setTags({}); }
  }, [open]);

  const typeOptions = connection ? (TYPE_OPTIONS[connection.prov] || []) : [];

  return (
    <Modal open={open} onClose={onClose}
      title="Add resource"
      subtitle={connection ? <><span>In </span><span className="mono">{connection.name}</span></> : undefined}
      width={520}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="primary" icon="check" disabled={!name || !type}
          onClick={() => {
            onCreate({
              id: 'r_' + Math.random().toString(36).slice(2, 7),
              name, type, native: native || '(pending discovery)', mtd: 0, tags,
            });
            onClose();
          }}>
          Add resource
        </Button>
      </>}
    >
      <div className="fn-form">
        <label className="fn-field">
          <span className="fn-field-lbl">Name</span>
          <input className="fn-inp" autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="vm-api-prod-03" />
        </label>
        <label className="fn-field">
          <span className="fn-field-lbl">Type</span>
          <div className="fn-chips">
            {typeOptions.map(t => (
              <button key={t} className={`fn-chip ${type === t ? 'fn-chip-on' : ''}`} onClick={() => setType(t)}>{t}</button>
            ))}
          </div>
        </label>
        <label className="fn-field">
          <span className="fn-field-lbl">Provider ID (optional)</span>
          <input className="fn-inp mono" value={native} onChange={e => setNative(e.target.value)} placeholder="/subscriptions/.../resource" />
          <span className="fn-field-hint">Leave blank to auto-discover on next run.</span>
        </label>
        <div>
          <div className="fn-field-lbl" style={{ marginBottom: 8 }}>Tags</div>
          {Object.entries(TAG_VOCAB).slice(0, 3).map(([k, vs]) => (
            <div key={k} className="fn-tagrow">
              <span className="fn-k" style={{ width: 100 }}>{k}</span>
              <div className="fn-chips">
                {vs.map(v => (
                  <button key={v} className={`fn-chip ${tags[k] === v ? 'fn-chip-on' : ''}`}
                    onClick={() => setTags(t => ({ ...t, [k]: t[k] === v ? '' : v }))}>{v}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}
