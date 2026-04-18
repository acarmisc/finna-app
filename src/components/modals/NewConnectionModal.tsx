import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Icon } from '../common/Icon';
import { usePlugins } from '../../api/plugins';

interface NewConnectionModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (config: {
    provider: string;
    extractor_type: string;
    name: string;
    credential_type: string;
    config: Record<string, string>;
    scope: string;
  }) => void;
  forProjectId?: string | null;
}

const PROVIDER_COLORS: Record<string, string> = {
  azure: '#0078D4',
  gcp: '#4285F4',
  aws: '#FF9900',
  llm: '#8B5CF6',
  ecb: '#10B981',
};

export function NewConnectionModal({ open, onClose, onCreate, forProjectId }: NewConnectionModalProps) {
  const { plugins } = usePlugins();
  const [step, setStep] = useState(0);
  const [selectedType, setSelectedType] = useState('');
  const [auth, setAuth] = useState('');
  const [name, setName] = useState('');
  const [scope, setScope] = useState('');
  const [configValues, setConfigValues] = useState<Record<string, string>>({});

  const plugin = plugins.find(p => p.type === selectedType);

  useEffect(() => {
    if (open) {
      setStep(0);
      setSelectedType('');
      setAuth('');
      setName('');
      setScope('');
      setConfigValues({});
    }
  }, [open]);

  const steps = ['Provider', 'Authentication', 'Configuration', 'Confirm'];

  const canNext = [
    () => !!selectedType,
    () => !plugin || plugin.auth_methods.length === 0 || !!auth,
    () => name.trim().length > 1,
    () => true,
  ];

  const submit = () => {
    const config: Record<string, string> = { ...configValues };
    if (scope) config.scope = scope;
    onCreate({
      provider: plugin?.provider || selectedType.split('_')[0],
      extractor_type: selectedType,
      name,
      credential_type: auth || 'none',
      config,
      scope,
    });
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose}
      title="New connection"
      subtitle={`Step ${step + 1} of ${steps.length} · ${steps[step]}`}
      width={560}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        {step > 0 && <Button variant="outline" icon="arrow-left" onClick={() => setStep(step - 1)}>Back</Button>}
        {step < steps.length - 1
          ? <Button variant="primary" iconRight="arrow-right" disabled={!canNext[step]()} onClick={() => setStep(step + 1)}>Continue</Button>
          : <Button variant="primary" icon="check" onClick={submit}>Create connection</Button>}
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
        <div className="fn-choice-grid">
          {plugins.map(p => (
            <button key={p.type}
              className={`fn-choice ${selectedType === p.type ? 'is-active' : ''}`}
              onClick={() => { setSelectedType(p.type); setAuth(''); }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: PROVIDER_COLORS[p.provider] || 'var(--fg-muted)', flexShrink: 0 }} />
              <div>
                <div className="fn-choice-t">{p.display_name}</div>
                <div className="fn-choice-s">{p.description}</div>
              </div>
              {selectedType === p.type && <Icon name="check" size={14} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
            </button>
          ))}
        </div>
      )}

      {step === 1 && plugin && (
        <div className="fn-choice-col">
          {plugin.auth_methods.length > 0 ? plugin.auth_methods.map(m => (
            <button key={m.id} className={`fn-choice ${auth === m.id ? 'is-active' : ''}`} onClick={() => setAuth(m.id)}>
              <Icon name="key-round" size={16} style={{ color: 'var(--fg-muted)' }} />
              <div>
                <div className="fn-choice-t">{m.label}</div>
                <div className="fn-choice-s">{m.sub}</div>
              </div>
              {auth === m.id && <Icon name="check" size={14} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
            </button>
          )) : (
            <div style={{ padding: 'var(--s-4)', color: 'var(--fg-subtle)', fontSize: 'var(--fs-13)' }}>
              This plugin does not require authentication.
            </div>
          )}
        </div>
      )}

      {step === 2 && plugin && (
        <div className="fn-form">
          <label className="fn-field">
            <span className="fn-field-lbl">Connection name</span>
            <input className="fn-inp" autoFocus value={name} onChange={e => setName(e.target.value)}
              placeholder={`${plugin.provider}-prod`} />
            <span className="fn-field-hint">Shown in sidebar and run logs. Lowercase, no spaces.</span>
          </label>
          {plugin.config_fields.map(f => (
            <label key={f.name} className="fn-field">
              <span className="fn-field-lbl">{f.label}{f.required && ' *'}</span>
              {f.type === 'select' ? (
                <select className="fn-inp" value={configValues[f.name] || String(f.default || '')}
                  onChange={e => setConfigValues(v => ({ ...v, [f.name]: e.target.value }))}>
                  <option value="">Select...</option>
                  {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              ) : (
                <input className="fn-inp"
                  type={f.type === 'password' ? 'password' : 'text'}
                  value={configValues[f.name] || String(f.default || '')}
                  onChange={e => setConfigValues(v => ({ ...v, [f.name]: e.target.value }))}
                  placeholder={f.placeholder}
                />
              )}
              {f.required && <span className="fn-field-hint">Required</span>}
            </label>
          ))}
          <label className="fn-field">
            <span className="fn-field-lbl">Scope</span>
            <input className="fn-inp" value={scope} onChange={e => setScope(e.target.value)}
              placeholder={plugin.provider === 'gcp' ? 'project / dataset / table' : plugin.provider === 'azure' ? 'subscription-id or resource group' : 'host:port'} />
          </label>
        </div>
      )}

      {step === 3 && plugin && (
        <div className="fn-summary">
          <div className="fn-kv"><span className="fn-k">Provider</span><span className="fn-v">{plugin.display_name}</span></div>
          <div className="fn-kv"><span className="fn-k">Auth</span><span className="fn-v">{plugin.auth_methods.find(m => m.id === auth)?.label || 'None'}</span></div>
          <div className="fn-kv"><span className="fn-k">Name</span><span className="fn-v mono">{name || '—'}</span></div>
          <div className="fn-kv"><span className="fn-k">Scope</span><span className="fn-v mono">{scope || '(default)'}</span></div>
          <div className="fn-summary-note">
            <Icon name="info" size={14} />
            <span>Finna will attempt a dry-run extraction. No data is written until the first successful run.</span>
          </div>
        </div>
      )}
    </Modal>
  );
}