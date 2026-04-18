import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { FinProject } from '../../types';

interface NewProjectModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (p: FinProject) => void;
}

export function NewProjectModal({ open, onClose, onCreate }: NewProjectModalProps) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [owner, setOwner] = useState('');
  const [costCenter, setCostCenter] = useState('');
  const [budget, setBudget] = useState(5000);
  const [tags, setTags] = useState<Record<string, string>>({ env: 'prod', business_unit: 'core' });
  const { TAG_VOCAB } = FINNA_DATA;

  useEffect(() => {
    if (open) { setStep(0); setName(''); setSlug(''); setOwner(''); setCostCenter(''); setBudget(5000); setTags({ env: 'prod', business_unit: 'core' }); }
  }, [open]);

  useEffect(() => {
    if (name && !slug) setSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
  }, [name]);

  const steps = ['Basics', 'Governance', 'Tags', 'Confirm'];
  const canNext = [
    () => name.trim().length > 1 && slug.trim().length > 1,
    () => owner.trim().length > 3,
    () => true,
    () => true,
  ];

  const submit = () => {
    onCreate({
      id: 'p_' + Math.random().toString(36).slice(2, 7),
      name, slug, owner, costCenter: costCenter || 'unassigned',
      budgetCap: Number(budget) || 0, mtd: 0,
      tags, created: new Date().toISOString().slice(0, 10), note: '',
    });
    onClose();
  };

  const toggleTag = (k: string, v: string) =>
    setTags(t => ({ ...t, [k]: t[k] === v ? '' : v }));

  return (
    <Modal open={open} onClose={onClose}
      title="New project"
      subtitle={`Step ${step + 1} of ${steps.length} · ${steps[step]}`}
      width={560}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        {step > 0 && <Button variant="outline" icon="arrow-left" onClick={() => setStep(step - 1)}>Back</Button>}
        {step < steps.length - 1
          ? <Button variant="primary" iconRight="arrow-right" disabled={!canNext[step]()} onClick={() => setStep(step + 1)}>Continue</Button>
          : <Button variant="primary" icon="check" onClick={submit}>Create project</Button>}
      </>}
    >
      <div className="fn-stepper">
        {steps.map((s, i) => (
          <div key={s} className={`fn-step ${i === step ? 'is-active' : ''} ${i < step ? 'is-done' : ''}`}>
            <span className="fn-step-num">{i < step ? <Icon name="check" size={11} /> : i + 1}</span>
            <span>{s}</span>
          </div>
        ))}
      </div>

      {step === 0 && (
        <div className="fn-form">
          <label className="fn-field">
            <span className="fn-field-lbl">Project name</span>
            <input className="fn-inp" autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Platform, ML & AI, Analytics…" />
            <span className="fn-field-hint">Human-readable. Shown in sidebar and reports.</span>
          </label>
          <label className="fn-field">
            <span className="fn-field-lbl">Slug</span>
            <input className="fn-inp" value={slug} onChange={e => setSlug(e.target.value)} placeholder="platform" />
            <span className="fn-field-hint">URL-safe identifier. Lowercase, dashes only.</span>
          </label>
        </div>
      )}
      {step === 1 && (
        <div className="fn-form">
          <label className="fn-field">
            <span className="fn-field-lbl">Owner email</span>
            <input className="fn-inp" value={owner} onChange={e => setOwner(e.target.value)} placeholder="team@acme.co" />
            <span className="fn-field-hint">Primary contact. Gets budget notifications.</span>
          </label>
          <label className="fn-field">
            <span className="fn-field-lbl">Cost center</span>
            <input className="fn-inp" value={costCenter} onChange={e => setCostCenter(e.target.value)} placeholder="eng-001" />
            <span className="fn-field-hint">Propagated to all resources under this project.</span>
          </label>
          <label className="fn-field">
            <span className="fn-field-lbl">Monthly budget · USD</span>
            <input className="fn-inp" type="number" value={budget} onChange={e => setBudget(Number(e.target.value))} />
            <span className="fn-field-hint">Drives default alert at 80% utilization.</span>
          </label>
        </div>
      )}
      {step === 2 && (
        <div className="fn-form">
          <div className="fn-field-lbl" style={{ marginBottom: 6 }}>Default tags</div>
          <div className="fn-field-hint" style={{ marginBottom: 12 }}>Applied to all resources discovered within this project's connections.</div>
          {Object.entries(TAG_VOCAB).map(([k, vs]) => (
            <div key={k} className="fn-tagrow">
              <span className="fn-k" style={{ width: 120 }}>{k}</span>
              <div className="fn-chips">
                {vs.map(v => (
                  <button key={v} className={`fn-chip ${tags[k] === v ? 'fn-chip-on' : ''}`}
                    onClick={() => toggleTag(k, v)}>{v}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {step === 3 && (
        <div className="fn-summary">
          <div className="fn-kv"><span className="fn-k">Name</span><span className="fn-v">{name}</span></div>
          <div className="fn-kv"><span className="fn-k">Slug</span><span className="fn-v mono">{slug}</span></div>
          <div className="fn-kv"><span className="fn-k">Owner</span><span className="fn-v mono">{owner}</span></div>
          <div className="fn-kv"><span className="fn-k">Cost center</span><span className="fn-v mono">{costCenter || '—'}</span></div>
          <div className="fn-kv"><span className="fn-k">Budget</span><span className="fn-v mono">{fmt.money(Number(budget) || 0)}</span></div>
          <div className="fn-kv"><span className="fn-k">Tags</span><span className="fn-v">
            <div className="fn-chips">
              {Object.entries(tags).filter(([, v]) => v).map(([k, v]) => (
                <span key={k} className="fn-chip fn-chip-sm">{k}:<b>{v}</b></span>
              ))}
            </div>
          </span></div>
          <div className="fn-summary-note">
            <Icon name="info" size={14} />
            <span>You can add connections and resources after creating the project.</span>
          </div>
        </div>
      )}
    </Modal>
  );
}
