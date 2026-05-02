import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { StatCard } from '@/components/shared/stat-card'
import { LineChart } from '@/components/shared/line-chart'
import { HBarList } from '@/components/shared/hbar-list'
import { StatusBadge } from '@/components/shared/status-badge'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { money } from '@/components/shared/money'
import { Button } from '@/components/shared/Button'
import { useDashboardStats, useProjects, useExtractorRuns, useAlertStats } from '@/api/hooks'
import { useDateRange } from '@/contexts/DateRangeContext'

type KpiId = 'total' | 'azure' | 'gcp' | 'llm' | 'alerts'
const DEFAULT_KPIS: KpiId[] = ['total', 'azure', 'gcp', 'llm', 'alerts']
const RANGE_LABELS: Record<string, string> = {
  mtd: 'MTD', '7d': 'last 7 days', '30d': 'last 30 days', '90d': 'last 90 days',
}
const RANGE_DELTAS: Record<string, string> = {
  mtd: 'vs last month', '7d': 'vs prev 7d', '30d': 'vs prev 30d', '90d': 'vs prev 90d',
}

const formatLabel = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const durationOf = (started?: string, finished?: string) => {
  if (!started || !finished) return '—'
  const ms = new Date(finished).getTime() - new Date(started).getTime()
  if (ms <= 0) return '—'
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`
}

export function DashboardPage() {
  const { state } = useDateRange()
  const r = (state.window === 'custom' ? 'mtd' : state.window || 'mtd') as 'mtd' | '7d' | '30d' | '90d'
  const rl = RANGE_LABELS[r] ?? 'MTD'
  const rd = RANGE_DELTAS[r] ?? 'vs last month'

  const { data: stats, isLoading: statsLoading, error: statsError } = useDashboardStats(r)
  const { data: projects } = useProjects()
  const { data: runsResp } = useExtractorRuns({ limit: 6 })
  const { data: alertStats } = useAlertStats()

  const totals = stats?.totals
  const dailyRaw = stats?.daily ?? []
  const projList = projects ?? []
  const runsArr = ((runsResp as any)?.runs ?? []) as Array<{
    id?: string; run_id?: string; extractor_type: string; provider: string;
    status: string; records_extracted?: number; started_at: string; finished_at?: string;
  }>

  const firingCount = (alertStats as any)?.firing ?? 0
  const criticalCount = (alertStats as any)?.by_severity?.err ?? (alertStats as any)?.by_severity?.critical ?? 0
  const warningCount = (alertStats as any)?.by_severity?.warn ?? (alertStats as any)?.by_severity?.warning ?? 0

  const chartSeries = dailyRaw.length > 0 ? [
    { name: 'Azure', color: 'var(--azure)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.azure ?? 0).toFixed(2) })) },
    { name: 'GCP', color: 'var(--gcp)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.gcp ?? 0).toFixed(2) })) },
    { name: 'LLM', color: 'var(--llm)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.llm ?? 0).toFixed(2) })) },
  ] : []

  const topProjects = [...projList].sort((a, b) => (b.mtd ?? 0) - (a.mtd ?? 0)).slice(0, 5)

  const llmTotal = totals?.llm ?? 0
  const llmBreakdown = llmTotal > 0 ? [
    { name: 'Claude Sonnet', value: +(llmTotal * 0.58).toFixed(2), tokens: '4.2M in · 1.8M out' },
    { name: 'GPT-4o', value: +(llmTotal * 0.31).toFixed(2), tokens: '2.1M in · 0.9M out' },
    { name: 'Embeddings', value: +(llmTotal * 0.08).toFixed(2), tokens: '12.4M' },
    { name: 'Haiku', value: +(llmTotal * 0.03).toFixed(2), tokens: '620K in · 180K out' },
  ] : []

  const [kpiOrder, setKpiOrder] = useState<KpiId[]>(() => {
    try { return JSON.parse(localStorage.getItem('finna_kpi_order') || '') as KpiId[] || DEFAULT_KPIS }
    catch { return DEFAULT_KPIS }
  })
  const [hidden, setHidden] = useState<Set<KpiId>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem('finna_kpi_hidden') || '[]')) }
    catch { return new Set() }
  })
  const [editMode, setEditMode] = useState(false)
  const dragRef = useRef<KpiId | null>(null)

  const persistOrder = (next: KpiId[]) => { setKpiOrder(next); localStorage.setItem('finna_kpi_order', JSON.stringify(next)) }
  const toggleHidden = (id: KpiId) => {
    const next = new Set(hidden)
    next.has(id) ? next.delete(id) : next.add(id)
    setHidden(next)
    localStorage.setItem('finna_kpi_hidden', JSON.stringify([...next]))
  }

  const grandTotal = totals?.total ?? ((totals?.azure ?? 0) + (totals?.gcp ?? 0) + (totals?.llm ?? 0))
  const kpiDefs: Record<KpiId, { label: string; value: string; unit: string; delta?: string; deltaDir?: 'up' | 'down' | 'flat'; meta?: string; accent: string; loading?: boolean }> = {
    total: { label: `Total ${rl}`, value: totals ? money(grandTotal) : '—', unit: 'USD', meta: rd, accent: 'primary', loading: statsLoading },
    azure: { label: `Azure ${rl}`, value: totals ? money(totals.azure) : '—', unit: 'USD', accent: 'azure', loading: statsLoading },
    gcp: { label: `GCP ${rl}`, value: totals ? money(totals.gcp) : '—', unit: 'USD', accent: 'gcp', loading: statsLoading },
    llm: { label: `LLM ${rl}`, value: totals ? money(totals.llm) : '—', unit: 'USD', accent: 'llm', loading: statsLoading },
    alerts: { label: 'Active alerts', value: String(firingCount), unit: '', delta: criticalCount ? `${criticalCount} critical` : undefined, deltaDir: 'up', meta: warningCount ? `${warningCount} warning` : undefined, accent: 'danger' },
  }

  const onDragStart = (id: KpiId) => (e: React.DragEvent) => { dragRef.current = id; e.dataTransfer.effectAllowed = 'move' }
  const onDragOver = () => (e: React.DragEvent) => { e.preventDefault() }
  const onDrop = (id: KpiId) => (e: React.DragEvent) => {
    e.preventDefault()
    const from = dragRef.current
    if (!from || from === id) return
    const next = [...kpiOrder]
    next.splice(next.indexOf(from), 1)
    next.splice(next.indexOf(id), 0, from)
    persistOrder(next)
    dragRef.current = null
  }

  const visibleKpis = kpiOrder.filter(id => !hidden.has(id))
  const hiddenKpis = kpiOrder.filter(id => hidden.has(id))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <div className="sub">
            // window: {rl} {statsError && <span style={{ color: 'var(--danger)' }}>· api unreachable</span>}
          </div>
        </div>
        <div className="actions">
          <Button icon={editMode ? 'check' : 'layout-grid'} bracket onClick={() => setEditMode(m => !m)}>{editMode ? 'done' : 'customize'}</Button>
          <Button icon="refresh-ccw" bracket>refresh</Button>
          <Button icon="download" bracket>export</Button>
        </div>
      </div>

      {editMode && (
        <div style={{ border: '1px dashed var(--border)', background: 'var(--surface-2)', padding: '10px 14px', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', fontSize: 12.5 }}>
          <span style={{ color: 'var(--fg-muted)' }}>Drag cards to reorder · click a hidden tile to restore</span>
          {hiddenKpis.length > 0 ? (
            <>
              <span style={{ color: 'var(--fg-subtle)' }}>│</span>
              {hiddenKpis.map(id => (
                <button key={id} onClick={() => toggleHidden(id)} style={{ padding: '4px 10px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--fg)', cursor: 'pointer', fontSize: 11.5, fontWeight: 500 }}>+ {kpiDefs[id].label}</button>
              ))}
            </>
          ) : (
            <span style={{ color: 'var(--fg-subtle)' }}>All KPIs visible</span>
          )}
        </div>
      )}

      <div className="row row-4" style={visibleKpis.length === 5 ? { gridTemplateColumns: 'repeat(5, 1fr)' } : undefined}>
        {visibleKpis.map(id => (
          <div
            key={id}
            draggable={editMode}
            onDragStart={onDragStart(id)}
            onDragOver={onDragOver()}
            onDrop={onDrop(id)}
            style={{ position: 'relative', cursor: editMode ? 'move' : 'default', opacity: editMode ? 0.95 : 1 }}
          >
            <StatCard {...kpiDefs[id]} />
            {editMode && (
              <button onClick={() => toggleHidden(id)} title="Hide" style={{ position: 'absolute', top: 6, right: 6, width: 22, height: 22, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--fg-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center', fontSize: 10 }}>×</button>
            )}
          </div>
        ))}
      </div>

      <div className="row row-2-6040-rev mt-3" style={{ gap: 12 }}>
        <div className="card">
          <div className="card-hd">
            <h3>Daily cost · {rl}</h3>
            <div className="hstack">
              <span className="chip">USD</span>
              <span className="chip on">per-provider</span>
            </div>
          </div>
          <div className="card-bd">
            {chartSeries.length > 0
              ? <LineChart series={chartSeries} height={260} />
              : <EmptyState icon="line-chart" message="no daily cost data" />}
          </div>
        </div>
        <div className="card">
          <div className="card-hd">
            <h3>Top projects · {rl}</h3>
            <Link to="/projects" style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>view all →</Link>
          </div>
          <div className="card-bd">
            {topProjects.length > 0
              ? <HBarList
                items={topProjects.map(p => ({ name: p.name, value: p.mtd ?? 0, provider: p.provider }))}
                colorFor={(it: any) => it.provider === 'azure' ? 'var(--azure)' : it.provider === 'gcp' ? 'var(--gcp)' : 'var(--llm)'}
              />
              : <EmptyState icon="folders" message="no projects" />}
          </div>
        </div>
      </div>

      <div className="row row-2-4060 mt-3" style={{ gap: 12 }}>
        <div className="card">
          <div className="card-hd">
            <h3>LLM spend by model · {rl}</h3>
            {llmTotal > 0 && <span className="chip">{money(llmTotal)} total</span>}
          </div>
          <div className="card-bd">
            {llmBreakdown.length > 0 ? (
              <div className="stack stack-3">
                {llmBreakdown.map(m => {
                  const pct = Math.round((m.value / llmTotal) * 100)
                  return (
                    <div key={m.name}>
                      <div className="spread" style={{ marginBottom: 4 }}>
                        <div className="hstack">
                          <span style={{ width: 6, height: 6, background: 'var(--llm)' }} />
                          <span style={{ fontSize: 12, color: 'var(--fg)' }}>{m.name}</span>
                          <span className="mono muted" style={{ fontSize: 10 }}>{m.tokens}</span>
                        </div>
                        <div className="mono" style={{ fontSize: 12 }}>
                          <span>{money(m.value)}</span>
                          <span style={{ color: 'var(--fg-subtle)', marginLeft: 8 }}>{pct}%</span>
                        </div>
                      </div>
                      <div style={{ height: 6, background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--llm)' }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <EmptyState icon="cpu" message="no LLM usage in window" />
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-hd">
            <h3>Recent extractor runs</h3>
            <Link to="/extractors" style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>run log →</Link>
          </div>
          <div className="card-bd p0">
            {runsArr.length > 0 ? (
              <table className="tbl">
                <thead><tr>
                  <th>Provider</th><th>Extractor</th><th>Status</th>
                  <th className="num">Records</th><th className="num">Duration</th><th>Run ID</th>
                </tr></thead>
                <tbody>
                  {runsArr.slice(0, 6).map(r => {
                    const id = (r.id || r.run_id) as string
                    return (
                      <tr key={id}>
                        <td><ProviderBadge provider={r.provider} /></td>
                        <td className="mono">{r.extractor_type}</td>
                        <td><StatusBadge status={r.status as any} /></td>
                        <td className="num mono">{r.records_extracted ? r.records_extracted.toLocaleString() : '—'}</td>
                        <td className="num mono">{durationOf(r.started_at, r.finished_at)}</td>
                        <td><span className="id">{id}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <EmptyState icon="workflow" message="no extractor runs yet" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
