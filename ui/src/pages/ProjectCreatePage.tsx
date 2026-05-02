import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { useConnections, useCreateProject, useProjects } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import type { CloudConfigResponse, ProjectResponse } from '@/types/api'

const slugify = (s: string) =>
  s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48)

interface ConfigTypeaheadProps {
  configs: CloudConfigResponse[]
  selectedIds: string[]
  onChange: (ids: string[]) => void
}

function ConfigTypeahead({ configs, selectedIds, onChange }: ConfigTypeaheadProps) {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [hi, setHi] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  const selectedSet = new Set(selectedIds)
  const matches = configs.filter(c => {
    if (selectedSet.has(c.id)) return false
    if (!q) return true
    const needle = q.toLowerCase()
    const cfg = (c.config || {}) as Record<string, unknown>
    return c.name.toLowerCase().includes(needle)
      || c.provider.toLowerCase().includes(needle)
      || String(cfg.subscription_id ?? '').toLowerCase().includes(needle)
      || String(cfg.project_id ?? '').toLowerCase().includes(needle)
      || String(cfg.tenant_id ?? '').toLowerCase().includes(needle)
  }).slice(0, 8)

  useEffect(() => { setHi(0) }, [q, open])

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const add = (id: string) => { onChange([...selectedIds, id]); setQ(''); inputRef.current?.focus() }
  const remove = (id: string) => onChange(selectedIds.filter(x => x !== id))

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setHi(h => Math.min(h + 1, matches.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(h - 1, 0)) }
    else if (e.key === 'Enter' && open && matches[hi]) { e.preventDefault(); add(matches[hi].id) }
    else if (e.key === 'Backspace' && !q && selectedIds.length) { remove(selectedIds[selectedIds.length - 1]) }
    else if (e.key === 'Escape') { setOpen(false) }
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <div
        onClick={() => { inputRef.current?.focus(); setOpen(true) }}
        style={{
          display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6,
          minHeight: 40, padding: '6px 8px',
          background: 'var(--color-bg)', border: '1px solid var(--color-border)',
          cursor: 'text',
        }}>
        {selectedIds.map(id => {
          const c = configs.find(x => x.id === id)
          if (!c) return null
          return (
            <span key={id} className="hstack" style={{
              gap: 6, padding: '3px 4px 3px 8px',
              background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
              fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-fg)',
            }}>
              <ProviderBadge provider={c.provider} />
              <span>{c.name}</span>
              <button
                onClick={e => { e.stopPropagation(); remove(id) }}
                title="remove"
                style={{
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  width: 16, height: 16, padding: 0, background: 'transparent',
                  border: 'none', color: 'var(--color-fg-muted)', cursor: 'pointer',
                }}>
                <Icon name="x" size={12} />
              </button>
            </span>
          )
        })}
        <input
          ref={inputRef}
          value={q}
          onChange={e => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKey}
          placeholder={selectedIds.length ? '' : 'type to search configs · name, provider, subscription, project…'}
          style={{
            flex: 1, minWidth: 160, border: 'none', outline: 'none', background: 'transparent',
            color: 'var(--color-fg)', fontFamily: 'var(--font-mono)', fontSize: 12,
            padding: '4px 4px',
          }}
        />
      </div>

      {open && matches.length > 0 && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 20,
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          maxHeight: 280, overflowY: 'auto',
          boxShadow: '4px 4px 0 0 rgba(0,0,0,0.4)',
        }}>
          {matches.map((c, i) => {
            const cfg = (c.config || {}) as Record<string, unknown>
            const sub = cfg.subscription_id ? `sub · ${cfg.subscription_id}` : cfg.project_id ? `project · ${cfg.project_id}` : c.credential_type
            return (
              <button
                key={c.id}
                onMouseEnter={() => setHi(i)}
                onClick={() => add(c.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                  padding: '8px 10px', textAlign: 'left', cursor: 'pointer',
                  background: i === hi ? 'color-mix(in oklab, var(--color-primary) 14%, var(--color-surface))' : 'transparent',
                  border: 'none', borderBottom: '1px solid var(--color-border)',
                  color: 'var(--color-fg)', font: 'inherit',
                }}>
                <ProviderBadge provider={c.provider} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{c.name}</div>
                  <div className="mono muted" style={{ fontSize: 10, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {String(sub)}
                  </div>
                </div>
                <StatusBadge status="pending" />
              </button>
            )
          })}
        </div>
      )}

      {open && q && matches.length === 0 && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 20,
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          padding: '12px 14px',
        }}>
          <div className="mono muted" style={{ fontSize: 11 }}>// no configs match "{q}"</div>
          <div style={{ marginTop: 6 }}>
            <a
              href="#/configs/new"
              onClick={e => { e.preventDefault(); navigate('/configs/new') }}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
              + create new config →
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

export function ProjectCreatePage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { data: configs } = useConnections()
  const { data: projects } = useProjects()
  const createMut = useCreateProject()

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [configIds, setConfigIds] = useState<string[]>([])
  const [f, setF] = useState({
    name: '', slug: '', slugTouched: false,
    owner: '', cost_center: '',
    budget_cap: '', tags: '', note: '',
  })

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF(s => ({ ...s, [k]: v }))
  const setName = (v: string) =>
    setF(s => ({ ...s, name: v, slug: s.slugTouched ? s.slug : slugify(v) }))
  const setSlug = (v: string) => setF(s => ({ ...s, slug: slugify(v), slugTouched: true }))

  const existingSlugs = ((projects ?? []) as ProjectResponse[]).map(p => p.slug ?? '')
  const slugCollision = !!f.slug && existingSlugs.includes(f.slug)
  const budgetNum = Number(f.budget_cap)
  const budgetValid = f.budget_cap !== '' && !Number.isNaN(budgetNum) && budgetNum > 0
  const cfgList = (configs ?? []) as CloudConfigResponse[]
  const selectedConfigs = configIds.map(id => cfgList.find(c => c.id === id)).filter(Boolean) as CloudConfigResponse[]
  const providers = [...new Set(selectedConfigs.map(c => c.provider))]

  const canNext =
    (step === 1) ||
    (step === 2 && f.name.trim() && f.slug && !slugCollision && f.owner.trim() && f.cost_center.trim() && budgetValid) ||
    step === 3

  const submit = () => {
    const payload = {
      name: f.name.trim(),
      slug: f.slug,
      providers,
      config_ids: configIds,
      owner: f.owner.trim(),
      cost_center: f.cost_center.trim(),
      budget_cap: budgetNum,
      tags: f.tags.split(',').map(t => t.trim()).filter(Boolean),
      note: f.note.trim() || undefined,
    }
    createMut.mutate(payload, {
      onSuccess: () => {
        toast.showSuccess(`Project ${payload.name} created`)
        navigate('/projects')
      },
      onError: (err: any) => {
        toast.showError(err?.message || 'Failed to create project')
      },
    })
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <a
            href="#/projects"
            onClick={e => { e.preventDefault(); navigate('/projects') }}
            style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-fg-muted)' }}>
            ← projects
          </a>
          <h1 style={{ marginTop: 6 }}>New project</h1>
          <div className="sub">// 3-step setup · POST /api/v1/config/projects</div>
        </div>
      </div>

      <div className="steps">
        <span className={`step ${step > 1 ? 'done' : step === 1 ? 'on' : ''}`}>
          <span className="n">{step > 1 ? '✓' : '1'}</span>configs
        </span>
        <span className="sep">→</span>
        <span className={`step ${step > 2 ? 'done' : step === 2 ? 'on' : ''}`}>
          <span className="n">{step > 2 ? '✓' : '2'}</span>details
        </span>
        <span className="sep">→</span>
        <span className={`step ${step === 3 ? 'on' : ''}`}>
          <span className="n">3</span>review
        </span>
      </div>

      <div className="card">
        <div className="card-bd" style={{ padding: 24 }}>
          {step === 1 && (
            <div className="stack stack-4">
              <div>
                <div className="label spread">
                  <span>cloud configs</span>
                  <span className="mono muted" style={{ fontSize: 10, textTransform: 'none', letterSpacing: 0 }}>
                    // optional · pick any number · any mix of providers
                  </span>
                </div>
                <ConfigTypeahead configs={cfgList} selectedIds={configIds} onChange={setConfigIds} />
              </div>

              {selectedConfigs.length > 0 && (
                <div style={{ padding: 12, background: 'var(--color-bg)', border: '1px solid var(--color-border)' }}>
                  <div className="stat-lbl">selection summary</div>
                  <div className="hstack-3" style={{ marginTop: 8, flexWrap: 'wrap', gap: 8 }}>
                    <span className="mono" style={{ fontSize: 11 }}>
                      <b>{selectedConfigs.length}</b> config{selectedConfigs.length > 1 ? 's' : ''}
                    </span>
                    <span className="mono muted" style={{ fontSize: 11 }}>·</span>
                    <span className="mono" style={{ fontSize: 11 }}>providers ·</span>
                    {providers.map(p => <ProviderBadge key={p} provider={p} />)}
                  </div>
                </div>
              )}

              {selectedConfigs.length === 0 && (
                <div className="hint" style={{ padding: 12, background: 'var(--color-bg)', border: '1px dashed var(--color-border)' }}>
                  // you can also skip and link configs later ·{' '}
                  <a href="#/configs/new" onClick={e => { e.preventDefault(); navigate('/configs/new') }}>create new config →</a>
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="stack stack-4">
              <div className="row row-2">
                <div>
                  <div className="label">name *</div>
                  <input className="inp" placeholder="prod-platform" value={f.name} onChange={e => setName(e.target.value)} autoFocus />
                </div>
                <div>
                  <div className="label spread">
                    <span>slug *</span>
                    {f.slugTouched && (
                      <a
                        href="#"
                        onClick={e => { e.preventDefault(); setF(s => ({ ...s, slug: slugify(s.name), slugTouched: false })) }}
                        style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                        auto →
                      </a>
                    )}
                  </div>
                  <input
                    className="inp mono"
                    placeholder="prod-platform"
                    value={f.slug}
                    onChange={e => setSlug(e.target.value)}
                    style={slugCollision ? { borderColor: 'var(--color-danger)' } : undefined}
                  />
                  {slugCollision && <div className="hint" style={{ color: 'var(--color-danger)' }}>// slug already in use</div>}
                </div>
              </div>

              <div className="row row-2">
                <div>
                  <div className="label">owner *</div>
                  <input className="inp" placeholder="platform-eng" value={f.owner} onChange={e => set('owner', e.target.value)} />
                  <div className="hint">// team handle or email</div>
                </div>
                <div>
                  <div className="label">cost center *</div>
                  <input className="inp mono" placeholder="CC-1001" value={f.cost_center} onChange={e => set('cost_center', e.target.value)} />
                </div>
              </div>

              <div className="row row-2">
                <div>
                  <div className="label">monthly budget cap (USD) *</div>
                  <div className="inp-group">
                    <span className="mono muted" style={{ fontSize: 12, marginLeft: 10, flexShrink: 0 }}>$</span>
                    <input
                      className="inp mono"
                      placeholder="14000"
                      value={f.budget_cap}
                      onChange={e => set('budget_cap', e.target.value.replace(/[^0-9.]/g, ''))}
                    />
                  </div>
                  {f.budget_cap && !budgetValid && <div className="hint" style={{ color: 'var(--color-danger)' }}>// must be &gt; 0</div>}
                </div>
                <div>
                  <div className="label">tags</div>
                  <input className="inp mono" placeholder="prod, tier-1" value={f.tags} onChange={e => set('tags', e.target.value)} />
                  <div className="hint">// comma separated</div>
                </div>
              </div>

              <div>
                <div className="label">note</div>
                <textarea
                  className="inp"
                  rows={2}
                  placeholder="optional context · shown on project detail"
                  value={f.note}
                  onChange={e => set('note', e.target.value)}
                  style={{ resize: 'vertical', fontFamily: 'inherit' }}
                />
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="label">review</div>
              <div style={{ border: '1px solid var(--color-border)', background: 'var(--color-bg)', padding: 16, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                <div style={{ color: 'var(--color-fg-subtle)' }}># POST /api/v1/config/projects</div>
                <pre style={{ margin: 0, marginTop: 8, color: 'var(--color-fg)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {JSON.stringify({
                    name: f.name,
                    slug: f.slug,
                    providers: providers.length ? providers : '(none yet)',
                    config_ids: configIds.length ? configIds : '(none)',
                    owner: f.owner,
                    cost_center: f.cost_center,
                    budget_cap: budgetNum || 0,
                    tags: f.tags.split(',').map(t => t.trim()).filter(Boolean),
                    note: f.note || '(empty)',
                  }, null, 2)}
                </pre>
              </div>
              <div className="hint" style={{ marginTop: 10 }}>// MTD starts at 0 · cost rows populate after first extractor run</div>
            </div>
          )}
        </div>
        <div className="card-ft">
          <Button bracket disabled={step === 1} onClick={() => setStep(s => (Math.max(1, s - 1) as 1 | 2 | 3))}>← back</Button>
          {step < 3
            ? <Button variant="primary" bracket disabled={!canNext} onClick={() => setStep(s => ((s + 1) as 1 | 2 | 3))}>next step →</Button>
            : <Button variant="primary" bracket icon="check" onClick={submit} disabled={createMut.isPending}>
                {createMut.isPending ? 'creating…' : 'create project'}
              </Button>}
        </div>
      </div>
    </div>
  )
}

export default ProjectCreatePage
