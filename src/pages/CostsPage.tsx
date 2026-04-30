import { useState, useMemo } from 'react'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { CostDeltaCell } from '@/components/shared/cost-delta-cell'
import { StackedAreaChart } from '@/components/shared/stacked-area-chart'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'
import { money } from '@/components/shared/money'
import { useCosts, useDailyCosts, useProjects } from '@/api/hooks'
import { useDateRange } from '@/contexts/DateRangeContext'
import type { Provider, CostRecord } from '@/types/api'

function formatLabel(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function CostsPage() {
  const { state } = useDateRange()
  const [tab, setTab] = useState<'overview' | 'sku' | 'daily'>('overview')
  const [providers, setProviders] = useState<Record<Provider, boolean>>({ azure: true, gcp: true, llm: true, aws: false })
  const [projSel, setProjSel] = useState<string[]>([])
  const [sku, setSku] = useState('')
  const [applied, setApplied] = useState({ providers: { ...providers }, proj: [] as string[], sku: '' })

  const apply = () => setApplied({ providers: { ...providers }, proj: [...projSel], sku })
  const reset = () => {
    setProviders({ azure: true, gcp: true, llm: true, aws: false })
    setProjSel([])
    setSku('')
    setApplied({ providers: { azure: true, gcp: true, llm: true, aws: false }, proj: [], sku: '' })
  }

  const { data: costsResp } = useCosts({ startDate: state.start, endDate: state.end })
  const { data: dailyResp } = useDailyCosts({ startDate: state.start, endDate: state.end })
  const { data: projects } = useProjects()

  const allRows = (costsResp?.costs ?? []) as CostRecord[]
  const dailyRaw = dailyResp?.days ?? []

  const filtered = allRows.filter(c =>
    applied.providers[c.prov as Provider] &&
    (!applied.sku || c.sku.toLowerCase().includes(applied.sku.toLowerCase())) &&
    (applied.proj.length === 0 || applied.proj.includes(c.name))
  )

  const grouped = useMemo(() => {
    const acc: Record<string, { sku: string; count: number; mtd: number; prev: number; providers: Set<string> }> = {}
    filtered.forEach(c => {
      if (!acc[c.sku]) acc[c.sku] = { sku: c.sku, count: 0, mtd: 0, prev: 0, providers: new Set() }
      acc[c.sku].count++
      acc[c.sku].mtd += c.mtd
      acc[c.sku].prev += c.prev ?? 0
      acc[c.sku].providers.add(c.prov)
    })
    return Object.values(acc).sort((a, b) => b.mtd - a.mtd)
  }, [filtered])

  const subtotals = useMemo(() => {
    const acc: Record<Provider, { mtd: number; prev: number }> = { azure: { mtd: 0, prev: 0 }, gcp: { mtd: 0, prev: 0 }, llm: { mtd: 0, prev: 0 }, aws: { mtd: 0, prev: 0 } }
    filtered.forEach(c => {
      acc[c.prov as Provider].mtd += c.mtd
      acc[c.prov as Provider].prev += c.prev ?? 0
    })
    return acc
  }, [filtered])

  const grand = filtered.reduce((s, c) => s + c.mtd, 0)
  const grandPrev = filtered.reduce((s, c) => s + (c.prev ?? 0), 0)

  const dailySeries: any[] = []
  if (applied.providers.azure) dailySeries.push({ name: 'Azure', color: 'var(--azure)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.azure ?? 0).toFixed(2) })) })
  if (applied.providers.gcp) dailySeries.push({ name: 'GCP', color: 'var(--gcp)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.gcp ?? 0).toFixed(2) })) })
  if (applied.providers.llm) dailySeries.push({ name: 'LLM', color: 'var(--llm)', data: dailyRaw.map((d: any) => ({ label: formatLabel(d.date), value: +(d.llm ?? 0).toFixed(2) })) })

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Cost explorer</h1>
          <div className="sub">// {filtered.length} records · {money(grand)} · normalized USD · cost_records</div>
        </div>
        <div className="actions">
          <Button icon="filter" bracket>add filter</Button>
          <Button icon="download" variant="primary" bracket>export csv</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <h3>Filters</h3>
          <div className="hstack">
            <Button size="sm" onClick={reset} bracket>reset</Button>
            <Button size="sm" variant="primary" onClick={apply} bracket>apply filters</Button>
          </div>
        </div>
        <div className="card-bd">
          <div className="row" style={{ gridTemplateColumns: 'auto 1fr 1fr', alignItems: 'start', gap: 24 }}>
            <div>
              <div className="label">providers</div>
              <div className="stack stack-2">
                {(['azure', 'gcp', 'llm'] as const).map(p => (
                  <label key={p} className="checkbox">
                    <input type="checkbox" checked={providers[p]} onChange={e => setProviders(s => ({ ...s, [p]: e.target.checked }))} />
                    <span className="box" />
                    <ProviderBadge provider={p} />
                    <span className="mono">{p}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <div className="label">projects</div>
              <div className="stack stack-2" style={{ maxHeight: 120, overflowY: 'auto', border: '1px solid var(--border)', padding: 8, background: 'var(--bg)' }}>
                {(projects ?? []).map(p => (
                  <label key={p.id} className="checkbox">
                    <input type="checkbox" checked={projSel.includes(p.name)} onChange={e => {
                      setProjSel(s => e.target.checked ? [...s, p.name] : s.filter(x => x !== p.name))
                    }} />
                    <span className="box" />
                    {p.provider && <ProviderBadge provider={p.provider} />}
                    <span className="mono">{p.name}</span>
                  </label>
                ))}
                {(!projects || projects.length === 0) && (
                  <span className="muted mono" style={{ fontSize: 11 }}>// no projects</span>
                )}
              </div>
            </div>
            <div>
              <div className="label">SKU search</div>
              <div className="inp-group">
                <Icon name="search" size={14} />
                <input className="inp" placeholder="e.g. BigQuery, VM, Tokens…" value={sku} onChange={e => setSku(e.target.value)} />
              </div>
              <div className="hint">// applies after [apply filters]</div>
              <div className="mt-3">
                <div className="label">date range</div>
                <span className="chip" style={{ display: 'inline-flex' }}><Icon name="calendar" size={12} />&nbsp;{state.start} → {state.end}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="tabs mt-4">
        {(['overview', 'sku', 'daily'] as const).map(k => (
          <button key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>
            {k === 'overview' ? 'Overview' : k === 'sku' ? 'By SKU' : 'Daily trend'}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="card">
          <div className="card-hd">
            <h3>Records</h3>
            <span className="mono muted" style={{ fontSize: 11 }}>{filtered.length} rows · sum · {money(grand)}</span>
          </div>
          <div className="card-bd p0">
            {filtered.length === 0 ? (
              <EmptyState icon="search-x" title="No records" message="no cost records match your filters" />
            ) : (
              <table className="tbl">
                <thead><tr>
                  <th>Provider</th><th>Project</th><th>SKU</th>
                  <th className="num">MTD</th><th className="num">Previous</th><th className="num">Δ</th>
                </tr></thead>
                <tbody>
                  {filtered.map(r => (
                    <tr key={r.id}>
                      <td><ProviderBadge provider={r.prov} /></td>
                      <td className="mono">{r.name}</td>
                      <td>{r.sku}</td>
                      <td className="num mono">{money(r.mtd)}</td>
                      <td className="num mono muted">{money(r.prev ?? 0)}</td>
                      <td className="num"><CostDeltaCell value={r.delta ?? null} /></td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  {(['azure', 'gcp', 'llm'] as const).map(p => subtotals[p].mtd > 0 && (
                    <tr key={p}>
                      <td colSpan={3}>
                        <span className="hstack"><ProviderBadge provider={p} /><span className="uppercase mono" style={{ fontSize: 10 }}>{p} subtotal</span></span>
                      </td>
                      <td className="num mono">{money(subtotals[p].mtd)}</td>
                      <td className="num mono muted">{money(subtotals[p].prev)}</td>
                      <td className="num"><CostDeltaCell value={subtotals[p].prev ? ((subtotals[p].mtd - subtotals[p].prev) / subtotals[p].prev * 100) : 0} /></td>
                    </tr>
                  ))}
                  <tr>
                    <td colSpan={3}><b style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Grand total</b></td>
                    <td className="num mono"><b>{money(grand)}</b></td>
                    <td className="num mono muted">{money(grandPrev)}</td>
                    <td className="num"><CostDeltaCell value={grandPrev ? ((grand - grandPrev) / grandPrev * 100) : 0} /></td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'sku' && (
        <div className="card">
          <div className="card-hd"><h3>Grouped by SKU</h3><span className="mono muted" style={{ fontSize: 11 }}>{grouped.length} SKUs</span></div>
          <div className="card-bd p0">
            <table className="tbl">
              <thead><tr>
                <th>SKU</th><th>Providers</th><th className="num">Instances</th>
                <th className="num">MTD</th><th className="num">Previous</th><th className="num">Δ</th>
              </tr></thead>
              <tbody>
                {grouped.map(g => (
                  <tr key={g.sku}>
                    <td className="mono">{g.sku}</td>
                    <td><span className="hstack">{[...g.providers].map(p => <ProviderBadge key={p} provider={p as Provider} />)}</span></td>
                    <td className="num mono">{g.count}</td>
                    <td className="num mono">{money(g.mtd)}</td>
                    <td className="num mono muted">{money(g.prev)}</td>
                    <td className="num"><CostDeltaCell value={g.prev ? ((g.mtd - g.prev) / g.prev * 100) : 0} /></td>
                  </tr>
                ))}
                {grouped.length === 0 && (
                  <tr><td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 24 }}>// no records</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'daily' && (
        <div className="card">
          <div className="card-hd"><h3>Daily · stacked by provider</h3><span className="chip on">{state.start} → {state.end}</span></div>
          <div className="card-bd">
            {dailySeries.length === 0
              ? <EmptyState icon="chart-line" message="select at least one provider" />
              : <StackedAreaChart series={dailySeries} height={300} />}
          </div>
        </div>
      )}
    </div>
  )
}

export default CostsPage
