import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';

interface TagEditorModalProps {
  open: boolean;
  onClose: () => void;
  target: { name: string; tags: Record<string, string> } | null;
  onSave: (tags: Record<string, string>) => void;
}

export function TagEditorModal({ open, onClose, target, onSave }: TagEditorModalProps) {
  const { TAG_VOCAB } = FINNA_DATA;
  const [tags, setTags] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open && target) setTags({ ...target.tags });
  }, [open, target]);

  if (!target) return null;

  return (
    <Modal open={open} onClose={onClose}
      title="Edit tags"
      subtitle={<>for <span className="mono">{target.name}</span></>}
      width={520}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="primary" icon="check" onClick={() => { onSave(tags); onClose(); }}>Save tags</Button>
      </>}
    >
      <div className="fn-form">
        {Object.entries(TAG_VOCAB).map(([k, vs]) => (
          <div key={k} className="fn-tagrow" style={{ alignItems: 'flex-start' }}>
            <span className="fn-k" style={{ width: 120, paddingTop: 4 }}>{k}</span>
            <div className="fn-chips">
              {vs.map(v => (
                <button key={v} className={`fn-chip ${tags[k] === v ? 'fn-chip-on' : ''}`}
                  onClick={() => setTags(t => ({ ...t, [k]: t[k] === v ? '' : v }))}>{v}</button>
              ))}
              <button className="fn-chip fn-chip-add"
                onClick={() => { const v = prompt(`Value for "${k}"?`); if (v) setTags(t => ({ ...t, [k]: v })); }}>
                + custom
              </button>
            </div>
          </div>
        ))}
        <div className="fn-summary-note">
          <Icon name="info" size={14} />
          <span>Tags propagate to cost_records on next extraction. Existing rows are back-filled nightly.</span>
        </div>
      </div>
    </Modal>
  );
}
