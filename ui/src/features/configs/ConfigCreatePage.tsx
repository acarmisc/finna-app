import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'
import { useCreateConnection } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import type { Provider, CredentialType } from '@/types/api'

type Fields = {
  name: string
  tenant_id: string
  client_id: string
  client_secret: string
  subscription_id: string
  project_id: string
  key_file: string
  api_provider: 'anthropic' | 'openai' | 'azure-openai'
  api_key: string
  base_url: string
}

const initial: Fields = {
  name: '', tenant_id: '', client_id: '', client_secret: '', subscription_id: '',
  project_id: '', key_file: '',
  api_provider: 'anthropic', api_key: '', base_url: '',
}

export function ConfigCreatePage() {
  const navigate = useNavigate()
  const toast = useToast()
  const create = useCreateConnection()

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [prov, setProv] = useState<Provider | null>(null)
  const [cred, setCred] = useState<CredentialType>('service_principal')
  const [f, setF] = useState<Fields>(initial)
  const set = (k: keyof Fields, v: string) => setF(s => ({ ...s, [k]: v }))

  const validStep2 = (() => {
    if (!f.name) return false
    if (prov === 'azure') {
      if (cred === 'service_principal') return !!(f.tenant_id && f.client_id && f.client_secret && f.subscription_id)
      return !!f.subscription_id
    }
    if (prov === 'gcp') {
      return !!f.project_id && (cred !== 'service_principal' || !!f.key_file)
    }
    if (prov === 'llm') {
      return !!f.api_key
    }
    return false
  })()

  const canNext = (step === 1 && !!prov) || (step === 2 && validStep2) || step === 3

  const buildPayload = () => {
    const config: Record<string, unknown> = {}
    if (prov === 'azure') {
      config.tenant_id = f.tenant_id
      config.subscription_id = f.subscription_id
      if (cred === 'service_principal') {
        config.client_id = f.client_id
        config.client_secret = f.client_secret
      }
    } else if (prov === 'gcp') {
      config.project_id = f.project_id
      if (cred === 'service_principal' && f.key_file) config.key_file = f.key_file
    } else if (prov === 'llm') {
      config.api_provider = f.api_provider
      config.api_key = f.api_key
      if (f.base_url) config.base_url = f.base_url
    }
    return {
      provider: prov as 'azure' | 'gcp' | 'llm' | 'aws',
      name: f.name,
      credential_type: cred,
      ...(prov === 'llm' ? { api_provider: f.api_provider } : {}),
      config,
    }
  }

  const submit = () => {
    create.mutate(buildPayload(), {
      onSuccess: () => {
        toast.showSuccess(`Config ${f.name} created`)
        navigate('/configs')
      },
      onError: (e: any) => {
        toast.showError(e?.message ?? 'Failed to create config')
      },
    })
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <Link to="/configs" className="mono muted" style={{ fontSize: 11 }}>← configs</Link>
          <h1 style={{ marginTop: 6 }}>New cloud config</h1>
          <div className="sub">// 3-step setup · POST /api/v1/config</div>
        </div>
      </div>

      <div className="steps">
        <span className={`step ${step > 1 ? 'done' : step === 1 ? 'on' : ''}`}><span className="n">{step > 1 ? '✓' : '1'}</span>provider</span>
        <span className="sep">→</span>
        <span className={`step ${step > 2 ? 'done' : step === 2 ? 'on' : ''}`}><span className="n">{step > 2 ? '✓' : '2'}</span>credentials</span>
        <span className="sep">→</span>
        <span className={`step ${step === 3 ? 'on' : ''}`}><span className="n">3</span>review</span>
      </div>

      <div className="card">
        <div className="card-bd" style={{ padding: 24 }}>
          {step === 1 && (
            <div>
              <div className="label">select a provider</div>
              <div className="row row-2" style={{ marginTop: 8, gap: 12 }}>
                {[
                  { id: 'azure' as const, title: 'Microsoft Azure', desc: 'Cost Management export · subscription or RG scope', color: 'var(--azure)' },
                  { id: 'gcp' as const, title: 'Google Cloud', desc: 'BigQuery billing export · project scope', color: 'var(--gcp)' },
                  { id: 'llm' as const, title: 'LLM Provider', desc: 'Anthropic / OpenAI / Azure-OpenAI · per-token usage', color: 'var(--llm)' },
                  { id: 'aws' as const, title: 'AWS · soon', desc: 'Cost Explorer export · not yet implemented', color: 'var(--aws)', disabled: true },
                ].map(p => (
                  <button
                    key={p.id}
                    onClick={() => !p.disabled && setProv(p.id as Provider)}
                    disabled={p.disabled}
                    style={{
                      padding: 20, textAlign: 'left', cursor: p.disabled ? 'not-allowed' : 'pointer',
                      background: prov === p.id ? `color-mix(in oklab, ${p.color} 10%, var(--surface))` : 'var(--surface)',
                      border: `1px solid ${prov === p.id ? p.color : 'var(--border)'}`,
                      boxShadow: prov === p.id ? `inset 0 0 0 1px ${p.color}` : 'none',
                      color: 'inherit', font: 'inherit', display: 'flex', flexDirection: 'column', gap: 12,
                      opacity: p.disabled ? 0.5 : 1,
                    }}
                  >
                    <div className="hstack spread">
                      <ProviderBadge provider={p.id} size="lg" />
                      {prov === p.id && <span className="mono" style={{ fontSize: 10, color: p.color, textTransform: 'uppercase', letterSpacing: '0.1em' }}>✓ selected</span>}
                    </div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--fg)' }}>{p.title}</div>
                      <div className="mono muted" style={{ fontSize: 11, marginTop: 4 }}>{p.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && prov === 'azure' && (
            <div className="stack stack-4">
              <div>
                <div className="label">credential type</div>
                <select className="sel" value={cred} onChange={e => setCred(e.target.value as CredentialType)}>
                  <option value="service_principal">service_principal</option>
                  <option value="managed_identity">managed_identity</option>
                  <option value="cli">cli</option>
                  <option value="device_code">device_code</option>
                </select>
              </div>
              <div><div className="label">name *</div><input className="inp" placeholder="acme-prod-azure" value={f.name} onChange={e => set('name', e.target.value)} /></div>
              {cred === 'service_principal' && <>
                <div><div className="label">tenant id *</div><input className="inp" placeholder="8f2c-…-a1e9" value={f.tenant_id} onChange={e => set('tenant_id', e.target.value)} /></div>
                <div className="row row-2" style={{ gap: 12 }}>
                  <div><div className="label">client id *</div><input className="inp" value={f.client_id} onChange={e => set('client_id', e.target.value)} /></div>
                  <div><div className="label">client secret *</div><input type="password" className="inp" value={f.client_secret} onChange={e => set('client_secret', e.target.value)} /></div>
                </div>
              </>}
              <div><div className="label">subscription id *</div><input className="inp" placeholder="00000000-0000-0000-…" value={f.subscription_id} onChange={e => set('subscription_id', e.target.value)} /></div>
            </div>
          )}

          {step === 2 && prov === 'gcp' && (
            <div className="stack stack-4">
              <div>
                <div className="label">credential type</div>
                <select className="sel" value={cred} onChange={e => setCred(e.target.value as CredentialType)}>
                  <option value="service_principal">service account key</option>
                  <option value="cli">cli (gcloud adc)</option>
                </select>
              </div>
              <div><div className="label">name *</div><input className="inp" placeholder="prod-platform-gcp" value={f.name} onChange={e => set('name', e.target.value)} /></div>
              <div><div className="label">project id *</div><input className="inp" placeholder="acme-prod-platform" value={f.project_id} onChange={e => set('project_id', e.target.value)} /></div>
              {cred === 'service_principal' && (
                <div>
                  <div className="label">service account key (JSON) *</div>
                  <div style={{ border: '1px dashed var(--border)', padding: 16, background: 'var(--bg)', textAlign: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--fg-muted)' }}>
                    <Icon name="upload" size={16} />
                    <div style={{ marginTop: 6 }}>
                      {f.key_file ? <span style={{ color: 'var(--accent)' }}>✓ {f.key_file}</span> : 'drop key.json here or click to select'}
                    </div>
                    <Button size="sm" bracket onClick={() => set('key_file', 'sa-acme-prod.json')} className="mt-2">browse</Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 2 && prov === 'llm' && (
            <div className="stack stack-4">
              <div><div className="label">name *</div><input className="inp" placeholder="acme-llm-gateway" value={f.name} onChange={e => set('name', e.target.value)} /></div>
              <div>
                <div className="label">api provider *</div>
                <select className="sel" value={f.api_provider} onChange={e => set('api_provider', e.target.value)}>
                  <option value="anthropic">anthropic</option>
                  <option value="openai">openai</option>
                  <option value="azure-openai">azure-openai</option>
                </select>
              </div>
              <div><div className="label">api key *</div><input type="password" className="inp" placeholder="sk-…" value={f.api_key} onChange={e => set('api_key', e.target.value)} /></div>
              <div><div className="label">base url (optional)</div><input className="inp" placeholder="https://api.openai.com/v1" value={f.base_url} onChange={e => set('base_url', e.target.value)} /></div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="label">review</div>
              <div style={{ border: '1px solid var(--border)', background: 'var(--bg)', padding: 16, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
                <div style={{ color: 'var(--fg-subtle)' }}># POST /api/v1/config</div>
                <pre style={{ margin: 0, marginTop: 8, color: 'var(--fg)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {JSON.stringify(
                    {
                      ...buildPayload(),
                      config: Object.fromEntries(
                        Object.entries(buildPayload().config).map(([k, v]) =>
                          ['client_secret', 'api_key'].includes(k) ? [k, v ? '••••••••' : '(unset)'] : [k, v ?? '(unset)']
                        )
                      ),
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
              <div className="hint" style={{ marginTop: 10 }}>// secrets are encrypted at rest · stored in cloud_config table</div>
            </div>
          )}
        </div>
        <div className="card-ft">
          <Button bracket disabled={step === 1} onClick={() => setStep(s => (Math.max(1, s - 1) as 1 | 2 | 3))}>← back</Button>
          {step < 3
            ? <Button variant="primary" bracket disabled={!canNext} onClick={() => setStep(s => ((s + 1) as 1 | 2 | 3))}>next step →</Button>
            : <Button variant="primary" bracket icon="check" disabled={create.isPending} onClick={submit}>{create.isPending ? 'creating…' : 'create config'}</Button>}
        </div>
      </div>
    </div>
  )
}

export default ConfigCreatePage
