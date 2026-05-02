import { useState, useMemo, Fragment } from 'react'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/shared/Button'
import { useConnections, useExtractorRuns, useTriggerExtractor, useExtractorLogs } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import { useQueryClient } from '@tanstack/react-query'
import type { Provider } from '@/types/api'

type Run = {
  id: string
  config_id?: string
  extractor_type: string
  provider: Provider | string
  status: string
  started_at?: string
  finished_at?: string
  records_extracted?: number
  error_message?: string
}

const fmt = (iso?: string) => iso ? new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

const dur = (started?: string, finished?: string, status?: string) => {
  if (!started) return '—'
  if (!finished && status !== 'completed' && status !== 'failed') return '—'
  if (!finished) return '—'
  const ms = new Date(finished).getTime() - new Date(started).getTime()
  if (ms <= 0) return '—'
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`
}

function ExtractorLogs({ runId }: { runId: string }) {
  const { data, error, isLoading } = useExtractorLogs(runId)
  
  if (isLoading) return <div className="hint">// fetching logs...</div>
  if (error) return <div className="hint">error loading logs</div>
  if (!data?.logs?.length) return <div className="empty" style={{ padding: 16 }}><div className="msg">no logs available</div></div>
  
  return (
    <pre className="mono" style={{ fontSize: 11, margin: 0, background: 'var(--surface)', border: '1px solid var(--border)', padding: 10, color: 'var(--fg)', maxHeight: 200, overflowY: 'auto' }}>
      {data.logs.join('\n')}
    </pre>
  )
}

export function ExtractorsPage() {
  const qc = useQueryClient()
  const toast = useToast()
  const { data: connsData } = useConnections()
  const { data: runsData } = useExtractorRuns({ limit: 50 })
  const trigger = useTriggerExtractor()

  const configs = (connsData ?? []).map(c => ({ id: c.id, name: c.name, provider: c.provider as Provider }))

  const runsArr = useMemo<Run[]>(() => {
    const raw = (runsData as any)?.runs
    if (!raw || raw.length === 0) return []
    return raw.map((r: any) => ({
      id: r.id ?? r.run_id,
      config_id: r.config_id,
      extractor_type: r.extractor_type,
      provider: r.provider,
      status: r.status,
      started_at: r.started_at,
      finished_at: r.finished_at,
      records_extracted: r.records_extracted,
      error_message: r.error_message ?? r.error,
    }))
  }, [runsData])

  const [sel, setSel] = useState<string>(configs[0]?.id ?? '')
  const [extType, setExtType] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [provFilter, setProvFilter] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [pollingId, setPollingId] = useState<string | null>(null)

  const filtered = runsArr.filter(r =>
    (statusFilter === 'all' || r.status === statusFilter) &&
    (provFilter === 'all' || r.provider === provFilter)
  )

  const onTrigger = () => {
    if (!sel) return
    trigger.mutate({ config_id: sel, extractor_type: extType || undefined }, {
      onSuccess: (res: any) => {
        const id = res?.data?.run_id ?? res?.run_id
        toast.showInfo(`Started run ${id ?? '(new)'}`)
        setPollingId(id ?? null)
        qc.invalidateQueries({ queryKey: ['extractor-runs'] })
      },
      onError: (e: any) => toast.showError(e?.message ?? 'Failed to trigger extractor'),
    })
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Extractors</h1>
          <div className="sub">// {filtered.length} runs · auto-refresh every 10s · extractor_runs table</div>
        </div>
        <div className="actions">
          <Button icon="refresh-ccw" bracket onClick={() => qc.invalidateQueries({ queryKey: ['extractor-runs'] })}>refresh</Button>
        </div>
      </div>

      <div className="row" style={{ gridTemplateColumns: '40% 1fr', gap: 12 }}>
        <div className="card" style={{ alignSelf: 'start' }}>
          <div className="card-hd"><h3>Trigger run</h3><span className="chip">POST /extractors/run</span></div>
          <div className="card-bd stack stack-4">
            <div>
              <div className="label">config *</div>
              <select className="sel" value={sel} onChange={e => setSel(e.target.value)}>
                {configs.map(c => <option key={c.id} value={c.id}>{c.name} · {c.provider}</option>)}
              </select>
            </div>
            <div>
              <div className="label">extractor type (optional)</div>
              <input className="inp" placeholder="e.g. azure_cost, gcp_billing" value={extType} onChange={e => setExtType(e.target.value)} />
              <div className="hint">// blank · defaults based on provider</div>
            </div>
            <div>
              <Button variant="primary" block bracket icon="play" disabled={trigger.isPending || !sel} onClick={onTrigger}>
                {trigger.isPending ? 'starting…' : 'run extractor'}
              </Button>
            </div>
            {pollingId && (
              <div style={{ padding: 12, background: 'var(--bg)', border: '1px solid var(--border)' }}>
                <div className="stat-lbl">polling</div>
                <div className="mono mt-2" style={{ fontSize: 12 }}>run_id · <b>{pollingId}</b></div>
                <div className="mt-2"><StatusBadge status={runsArr.find(r => r.id === pollingId)?.status ?? 'started'} /></div>
                <div className="hint mt-2">// GET /extractors/status?run_id={pollingId} · every 3s</div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-hd">
            <h3>Run history</h3>
            <div className="hstack">
              <select className="sel" style={{ width: 'auto' }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="all">status: all</option>
                <option value="running">running</option>
                <option value="completed">completed</option>
                <option value="failed">failed</option>
              </select>
              <select className="sel" style={{ width: 'auto' }} value={provFilter} onChange={e => setProvFilter(e.target.value)}>
                <option value="all">provider: all</option>
                <option value="azure">azure</option>
                <option value="gcp">gcp</option>
                <option value="llm">llm</option>
              </select>
            </div>
          </div>
          <div className="card-bd p0" style={{ maxHeight: 640, overflowY: 'auto' }}>
            <table className="tbl">
              <thead><tr>
                <th>Status</th><th>Run ID</th><th>Extractor</th><th>Provider</th>
                <th>Started</th><th>Finished</th><th className="num">Records</th><th className="num">Duration</th>
              </tr></thead>
              <tbody>
                {filtered.map(r => (
                  <Fragment key={r.id}>
                    <tr className="clickable" onClick={() => setExpanded(e => e === r.id ? null : r.id)}>
                      <td><StatusBadge status={r.status} /></td>
                      <td><span className="id">{r.id}</span></td>
                      <td className="mono">{r.extractor_type}</td>
                      <td><ProviderBadge provider={r.provider} /></td>
                      <td className="mono muted">{fmt(r.started_at)}</td>
                      <td className="mono muted">{fmt(r.finished_at)}</td>
                      <td className="num mono">{r.records_extracted ? r.records_extracted.toLocaleString() : '—'}</td>
                      <td className="num mono">{dur(r.started_at, r.finished_at, r.status)}</td>
                    </tr>
                    {expanded === r.id && (
                      <tr>
                        <td colSpan={8} style={{ background: 'var(--bg)', padding: 16 }}>
                          <div className="row row-2" style={{ gap: 12 }}>
                            <div>
                              <div className="label">run details</div>
                              <pre className="mono" style={{ fontSize: 11, margin: 0, background: 'var(--surface)', border: '1px solid var(--border)', padding: 10, color: 'var(--fg)' }}>
                                {JSON.stringify({ run_id: r.id, extractor: r.extractor_type, provider: r.provider, config_id: r.config_id, status: r.status, records: r.records_extracted ?? 0 }, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div className="label">logs / stderr</div>
                              <ExtractorLogs runId={r.id} />
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="muted" style={{ textAlign: 'center', padding: 24 }}>// no runs match filters</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExtractorsPage
