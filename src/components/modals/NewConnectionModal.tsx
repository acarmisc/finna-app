import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Icon } from '../common/Icon';
import { ProviderDot } from '../common/ProviderTag';
import type { Connection } from '../../types';

interface NewConnectionModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (conn: Connection) => void;
  forProjectId?: string | null;
}

const PROVIDERS = [
  { id: 'azure', label: 'Azure', sub: 'Cost Management API' },
  { id: 'gcp', label: 'GCP', sub: 'BigQuery billing export' },
  { id: 'aws', label: 'AWS', sub: 'Cost Explorer (coming)', disabled: true },
  { id: 'llm', label: 'OTel / LLM', sub: 'OpenTelemetry collector' },
] as const;

type ProvId = 'azure' | 'gcp' | 'aws' | 'llm';

const AUTH_METHODS: Record<string, { id: string; label: string; sub: string }[]> = {
  azure: [
    { id: 'device', label: 'Device code (browser)', sub: 'Recommended for local dev · cached in OS keyring' },
    { id: 'sp', label: 'Service principal', sub: 'Client ID + secret · for production' },
    { id: 'cli', label: 'Azure CLI', sub: 'Uses current `az login` session' },
  ],
  gcp: [
    { id: 'adc', label: 'Application Default Credentials', sub: 'Uses `gcloud auth login`' },
    { id: 'sakey', label: 'Service account JSON key', sub: 'Least-privilege IAM · roles/bigquery.dataViewer' },
  ],
  llm: [
    { id: 'otlp', label: 'OTLP endpoint', sub: 'gRPC · port 4317' },
  ],
  aws: [],
};

export function NewConnectionModal({ open, onClose, onCreate, forProjectId }: NewConnectionModalProps) {
  const [step, setStep] = useState(0);
  const [prov, setProv] = useState<ProvId>('azure');
  const [auth, setAuth] = useState('device');
  const [name, setName] = useState('');
  const [scope, setScope] = useState('');

  useEffect(() => {
    if (open) { setStep(0); setProv('azure'); setAuth('device'); setName(''); setScope(''); }
  }, [open]);

  const steps = ['Provider', 'Authentication', 'Scope', 'Confirm'];
  const canNext = [
    () => !!prov && !PROVIDERS.find(p => p.id === prov)?.disabled,
    () => !!auth,
    () => name.trim().length > 1,
    () => true,
  ];

  const submit = () => {
    const authLabel = AUTH_METHODS[prov]?.find(a => a.id === auth)?.label || auth;
    const defaultScope = prov === 'gcp' ? 'BQ billing export' : prov === 'azure' ? 'Subscription · Cost Management Reader' : 'OTel collector · 0.0.0.0:4317';
    onCreate({
      id: 'c_' + Math.random().toString(36).slice(2, 7),
      prov,
      name,
      scope: scope || defaultScope,
      status: 'ok',
      lastRun: 'just now',
      rows: '0',
      auth: authLabel,
      expires: auth === 'device' ? 'in 90 days' : auth === 'sp' ? 'in 365 days' : 'n/a',
      projectId: forProjectId ?? null,
      resources: [],
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
          {PROVIDERS.map(p => (
            <button key={p.id} disabled={'disabled' in p && p.disabled}
              className={`fn-choice ${prov === p.id ? 'is-active' : ''}`}
              onClick={() => !('disabled' in p && p.disabled) && setProv(p.id as ProvId)}>
              <ProviderDot p={p.id} />
              <div>
                <div className="fn-choice-t">{p.label}{'disabled' in p && p.disabled && <span className="fn-badge fn-b-neu" style={{ marginLeft: 6 }}>soon</span>}</div>
                <div className="fn-choice-s">{p.sub}</div>
              </div>
              {prov === p.id && <Icon name="check" size={14} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
            </button>
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="fn-choice-col">
          {(AUTH_METHODS[prov] || []).map(m => (
            <button key={m.id} className={`fn-choice ${auth === m.id ? 'is-active' : ''}`} onClick={() => setAuth(m.id)}>
              <Icon name="key-round" size={16} style={{ color: 'var(--fg-muted)' }} />
              <div>
                <div className="fn-choice-t">{m.label}</div>
                <div className="fn-choice-s">{m.sub}</div>
              </div>
              {auth === m.id && <Icon name="check" size={14} style={{ marginLeft: 'auto', color: 'var(--primary)' }} />}
            </button>
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="fn-form">
          <label className="fn-field">
            <span className="fn-field-lbl">Connection name</span>
            <input className="fn-inp" autoFocus value={name} onChange={e => setName(e.target.value)}
              placeholder={prov === 'azure' ? 'acme-prod' : prov === 'gcp' ? 'prod-platform' : 'otel-gateway-us'} />
            <span className="fn-field-hint">Shown in sidebar and run logs. Lowercase, no spaces.</span>
          </label>
          <label className="fn-field">
            <span className="fn-field-lbl">Scope</span>
            <input className="fn-inp" value={scope} onChange={e => setScope(e.target.value)}
              placeholder={prov === 'azure' ? 'subscription-id or resource group' : prov === 'gcp' ? 'project / dataset / table' : 'host:port'} />
            <span className="fn-field-hint">
              {prov === 'azure' ? 'Subscription ID, or RG list for narrower scope.'
                : prov === 'gcp' ? 'BigQuery dataset containing the billing export.'
                : 'OTLP gRPC endpoint for the OTel Collector.'}
            </span>
          </label>
        </div>
      )}

      {step === 3 && (
        <div className="fn-summary">
          <div className="fn-kv"><span className="fn-k">Provider</span><span className="fn-v"><ProviderDot p={prov} />{prov.toUpperCase()}</span></div>
          <div className="fn-kv"><span className="fn-k">Auth</span><span className="fn-v">{AUTH_METHODS[prov]?.find(a => a.id === auth)?.label}</span></div>
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
