import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { Dialog } from '@/components/shared/dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/shared/Button'
import { useConnections, useTestConnection, useDeleteConnection } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import type { Provider } from '@/types/api'

type ConfigRow = {
  id: string
  name: string
  provider: Provider | string
  credential_type: string
  tenant_id?: string
  subscription_id?: string
  project_id?: string
  created_at?: string
  last_test?: string
  last_test_at?: string
  err?: string | null
}

const normalize = (c: any): ConfigRow => {
  const cfg = c.config || {}
  return {
    id: c.id,
    name: c.name,
    provider: c.provider,
    credential_type: c.credential_type,
    tenant_id: cfg.tenant_id,
    subscription_id: cfg.subscription_id,
    project_id: cfg.project_id,
    created_at: c.created_at ? new Date(c.created_at).toLocaleDateString() : undefined,
    last_test: c.last_test ?? 'pending',
    last_test_at: c.last_test_at,
    err: c.error_message ?? c.err,
  }
}

export function ConfigsListPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { data } = useConnections()
  const testMut = useTestConnection()
  const delMut = useDeleteConnection()

  const [confirmDel, setConfirmDel] = useState<ConfigRow | null>(null)
  const [flash, setFlash] = useState<Record<string, 'ok' | 'err'>>({})

  const list: ConfigRow[] = (data ?? []).map(normalize)
  const failures = list.filter(c => c.last_test === 'failed' || c.err).length

  const testConn = (c: ConfigRow) => {
    testMut.mutate(c.id, {
      onSuccess: (res: any) => {
        const ok = res?.data?.ok ?? true
        setFlash(f => ({ ...f, [c.id]: ok ? 'ok' : 'err' }))
        toast[ok ? 'showSuccess' : 'showError'](ok ? `Connection ${c.name} · OK` : `Connection ${c.name} failed`)
        setTimeout(() => setFlash(f => { const n = { ...f }; delete n[c.id]; return n }), 2200)
      },
      onError: () => {
        setFlash(f => ({ ...f, [c.id]: 'err' }))
        toast.showError(`Connection ${c.name} failed`)
        setTimeout(() => setFlash(f => { const n = { ...f }; delete n[c.id]; return n }), 2200)
      },
    })
  }

  const doDelete = () => {
    if (!confirmDel) return
    delMut.mutate(confirmDel.id, {
      onSuccess: () => { toast.showSuccess(`Deleted ${confirmDel.name}`); setConfirmDel(null) },
      onError: () => { toast.showError('Delete failed'); setConfirmDel(null) },
    })
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Cloud configs</h1>
          <div className="sub">// {list.length} configured · {failures} test failures in last 24h</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket onClick={() => navigate('/configs/new')}>new config</Button>
        </div>
      </div>

      {list.length === 0 ? (
        <EmptyState icon="plug" title="No cloud configs" message="add an Azure / GCP / LLM connection to start tracking costs" action={<Button variant="primary" bracket icon="plus" onClick={() => navigate('/configs/new')}>new config</Button>} />
      ) : (
      <div className="row row-3" style={{ gap: 12 }}>
        {list.map(c => {
          const f = flash[c.id]
          return (
            <div key={c.id} className="card" style={{ borderColor: f === 'ok' ? 'var(--accent)' : f === 'err' ? 'var(--danger)' : 'var(--border)', transition: 'border-color 150ms' }}>
              <div className="card-hd">
                <div>
                  <h3 style={{ color: 'var(--fg)', fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: 600 }}>{c.name}</h3>
                  <div className="mono muted" style={{ fontSize: 10, marginTop: 2 }}>{c.credential_type}</div>
                </div>
                <ProviderBadge provider={c.provider} size="lg" />
              </div>
              <div className="card-bd">
                <dl style={{ margin: 0, fontSize: 12, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 12px' }}>
                  {c.tenant_id && <><dt className="mono muted" style={{ fontSize: 10 }}>TENANT</dt><dd className="mono" style={{ margin: 0 }}>{c.tenant_id}</dd></>}
                  {c.subscription_id && <><dt className="mono muted" style={{ fontSize: 10 }}>SUB</dt><dd className="mono" style={{ margin: 0 }}>{c.subscription_id}</dd></>}
                  {c.project_id && <><dt className="mono muted" style={{ fontSize: 10 }}>PROJECT</dt><dd className="mono" style={{ margin: 0 }}>{c.project_id}</dd></>}
                  {c.created_at && <><dt className="mono muted" style={{ fontSize: 10 }}>CREATED</dt><dd className="mono" style={{ margin: 0 }}>{c.created_at}</dd></>}
                  <dt className="mono muted" style={{ fontSize: 10 }}>LAST TEST</dt>
                  <dd style={{ margin: 0 }}>
                    <span className="hstack">
                      <StatusBadge status={c.last_test ?? 'pending'} />
                      {c.last_test_at && <span className="mono muted" style={{ fontSize: 11 }}>{c.last_test_at}</span>}
                    </span>
                  </dd>
                </dl>
                {c.err && (
                  <div style={{ marginTop: 10, padding: '8px 10px', background: 'color-mix(in oklab, var(--danger) 12%, var(--surface))', border: '1px solid var(--danger)', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--danger)' }}>
                    // {c.err}
                  </div>
                )}
              </div>
              <div className="card-ft">
                <div className="hstack">
                  <Button size="sm" icon="edit-3" bracket onClick={() => navigate(`/configs/${c.id}`)}>edit</Button>
                  <Button size="sm" icon={testMut.isPending ? 'loader' : 'activity'} bracket disabled={testMut.isPending} onClick={() => testConn(c)}>
                    {testMut.isPending ? 'testing…' : 'test'}
                  </Button>
                </div>
                <Button size="sm" variant="ghost" icon="trash-2" onClick={() => setConfirmDel(c)}>delete</Button>
              </div>
            </div>
          )
        })}
      </div>
      )}

      <Dialog
        open={!!confirmDel}
        onClose={() => setConfirmDel(null)}
        title={`Delete config · ${confirmDel?.name ?? ''}`}
        actions={
          <>
            <Button onClick={() => setConfirmDel(null)} bracket>cancel</Button>
            <Button variant="danger" bracket onClick={doDelete} disabled={delMut.isPending}>
              {delMut.isPending ? 'deleting…' : 'delete'}
            </Button>
          </>
        }
      >
        <p>This will remove the config and stop all scheduled extractions using it. Historical cost records remain.</p>
        <p className="mono" style={{ color: 'var(--danger)', marginTop: 12 }}>// this action cannot be undone</p>
      </Dialog>
    </div>
  )
}

export default ConfigsListPage
