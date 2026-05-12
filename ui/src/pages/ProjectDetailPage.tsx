import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { ProgressBar } from '@/components/shared/progress-bar'
import { CostDeltaCell } from '@/components/shared/cost-delta-cell'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/shared/Button'
import { money } from '@/components/shared/money'
import { useProject, useCosts } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import { useDateRange } from '@/contexts/DateRangeContext'
import type { Provider } from '@/types/api'
import { Icon } from '@/components/shared/Icon'

function Sparkline({ seed = 1, up = true }: { seed?: number; up?: boolean }) {
  const len = 12
  const pts = Array.from({ length: len }, (_, i) => {
    const n = Math.sin(seed + i * 0.9) * 0.3 + Math.cos(i * 0.5) * 0.2 + (up ? i * 0.08 : -i * 0.06)
    return { x: i, y: n }
  })
  const ys = pts.map(p => p.y)
  const miny = Math.min(...ys)
  const maxy = Math.max(...ys)
  const w = 140, h = 28
  const path = pts.map((p, i) => {
    const x = (p.x / (len - 1)) * w
    const y = h - ((p.y - miny) / (maxy - miny + 0.001)) * h
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <path d={path} fill="none" stroke={up ? 'var(--danger)' : 'var(--accent)'} strokeWidth="1.5" />
    </svg>
  )
}

const tagsToList = (tags?: any): string[] => {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return Object.entries(tags).map(([k, v]) => v && v !== 'true' ? `${k}:${v}` : k)
}

export function ProjectDetailPage() {
  const navigate = useNavigate()
  const { slug = '' } = useParams<{ slug: string }>()
  const toast = useToast()
  const { state } = useDateRange()
  const { data: p, isLoading } = useProject(slug)
  const { data: costsResp } = useCosts({ project: slug, startDate: state.start, endDate: state.end })

  const [note, setNote] = useState('')
  const [showDel, setShowDel] = useState(false)
  const [skuFilter, setSkuFilter] = useState('')
  useEffect(() => { setNote((p as any)?.note ?? '') }, [(p as any)?.note])

  const skus = useMemo(
    () => costsResp?.costs?.map(c => ({ sku: c.sku, mtd: c.mtd, prev: c.prev ?? 0, delta: c.delta ?? 0 })) ?? [],
    [costsResp]
  )

  const filteredSkus = useMemo(() => {
    if (!skuFilter.trim()) return skus
    const q = skuFilter.toLowerCase()
    return skus.filter(c => c.sku.toLowerCase().includes(q))
  }, [skus, skuFilter])

  const handleDelete = async () => {
    const token = localStorage.getItem('finna_token')
    const res = await fetch(`/api/v1/config/projects/${slug}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      toast.showSuccess('Project deleted')
      navigate('/projects')
    } else {
      toast.showError('Failed to delete project')
    }
    setShowDel(false)
  }

  if (isLoading) {
    return <div className="page"><div className="muted mono" style={{ textAlign: 'center', padding: 48 }}>// loading project…</div></div>
  }

  if (!p) {
    return (
      <div className="page">
        <EmptyState
          icon="search-x"
          title="Project not found"
          message={`no project matches slug "${slug}"`}
          action={<Button onClick={() => navigate('/projects')} bracket>back to projects</Button>}
        />
      </div>
    )
  }

  const cap = p.budget_cap ?? 0
  const mtd = p.mtd ?? 0
  const pct = cap > 0 ? (mtd / cap) * 100 : 0
  const provider = (p.provider ?? 'azure') as Provider

  const tags = tagsToList(p.tags)
  const totalMtd = skus.reduce((s, c) => s + c.mtd, 0)
  const totalPrev = skus.reduce((s, c) => s + c.prev, 0)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <Link to="/projects" className="mono muted" style={{ fontSize: 11 }}>← projects</Link>
          <h1 style={{ marginTop: 6 }}>
            <span className="hstack-3">
              <ProviderBadge provider={provider} size="lg" />
              {p.name}
            </span>
          </h1>
          <div className="hstack-3 sub" style={{ marginTop: 6, flexWrap: 'wrap' }}>
            <span>owner · <b style={{ color: 'var(--fg)' }}>{p.owner ?? '—'}</b></span>
            <span>cost_center · <b style={{ color: 'var(--fg)' }}>{p.cost_center ?? '—'}</b></span>
            <span>slug · <b style={{ color: 'var(--fg)' }}>{p.slug ?? slug}</b></span>
            {tags.length > 0 && <span>tags · {tags.map(t => <span key={t} className="chip" style={{ marginRight: 4 }}>{t}</span>)}</span>}
          </div>
        </div>
        <div className="actions">
          <Button icon="edit-3" bracket onClick={() => navigate('/projects')}>edit</Button>
          <Button icon="trash-2" variant="danger" bracket onClick={() => setShowDel(true)}>delete</Button>
        </div>
      </div>

      <div className="row row-2-6040-rev" style={{ gap: 12 }}>
        <div className="card">
          <div className="card-hd">
            <div className="hstack-3">
              <h3>Cost summary</h3>
              <span className="chip">custom range</span>
            </div>
          </div>
          <div className="card-bd">
            <div className="spread">
              <div>
                <div className="stat-lbl">total</div>
                <div className="stat-val" style={{ fontSize: 32 }}>{money(totalMtd)}<span className="ccy">USD</span></div>
              </div>
              {cap > 0 && (
                <div style={{ textAlign: 'right' }}>
                  <div className="stat-lbl">cap</div>
                  <div className="stat-val" style={{ fontSize: 20, color: 'var(--fg-muted)' }}>{money(cap, 0)}</div>
                  <div className="mono" style={{ fontSize: 11, color: pct >= 90 ? 'var(--danger)' : pct >= 70 ? 'var(--warning)' : 'var(--accent)', marginTop: 2 }}>
                    {pct >= 90 ? 'OVER' : pct >= 70 ? 'NEAR CAP' : 'OK'}
                  </div>
                </div>
              )}
            </div>
            {cap > 0 && (
              <div style={{ marginTop: 12 }}>
                <ProgressBar value={mtd} max={Math.max(cap, 1)} stepped segments={20} />
                <div className="hstack spread mt-2">
                  <span className="mono" style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{pct.toFixed(1)}% of cap</span>
                  <span className="mono" style={{ fontSize: 11 }}>{money(mtd)} / {money(cap, 0)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="card">
          <div className="card-hd"><h3>Notes</h3><span className="mono muted" style={{ fontSize: 10 }}>editable</span></div>
          <div className="card-bd">
            <textarea className="txt" rows={4} value={note} onChange={e => setNote(e.target.value)} placeholder="// operator notes…" style={{ resize: 'vertical', minHeight: 80 }} />
            <div className="hstack" style={{ justifyContent: 'flex-end', marginTop: 8 }}>
              <Button size="sm" onClick={() => toast.showSuccess('Notes saved')} bracket>save</Button>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd">
          <h3>Cost breakdown · SKU</h3>
          <div className="inp-group" style={{ maxWidth: 220, width: '100%' }}>
            <Icon name="search" size={13} />
            <input
              className="inp"
              placeholder="filter by SKU…"
              value={skuFilter}
              onChange={e => setSkuFilter(e.target.value)}
            />
          </div>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>SKU</th><th className="num">total</th><th className="num">prev</th><th className="num">Δ</th><th>Trend</th>
            </tr></thead>
            <tbody>
              {filteredSkus.map((c, i) => (
                <tr key={`${c.sku}-${i}`}>
                  <td className="mono">{c.sku}</td>
                  <td className="num mono">{money(c.mtd)}</td>
                  <td className="num mono muted">{money(c.prev)}</td>
                  <td className="num"><CostDeltaCell value={c.delta} /></td>
                  <td style={{ width: 160 }}><Sparkline seed={c.sku.length} up={c.delta > 0} /></td>
                </tr>
              ))}
              {filteredSkus.length === 0 && (
                <tr><td colSpan={5} className="muted" style={{ textAlign: 'center', padding: 24 }}>
                  {skus.length === 0 ? '// no cost records' : `// no SKU matches "${skuFilter}"`}
                </td></tr>
              )}
            </tbody>
            {filteredSkus.length > 0 && (
              <tfoot>
                <tr>
                  <td>Total</td>
                  <td className="num mono">{money(totalMtd)}</td>
                  <td className="num mono muted">{money(totalPrev)}</td>
                  <td></td><td></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {showDel && (
        <div className="dlg-scrim" onClick={() => setShowDel(false)}>
          <div className="dlg" onClick={e => e.stopPropagation()}>
            <div className="dlg-hd"><h3>Delete project?</h3></div>
            <div className="dlg-bd">
              <p className="mono" style={{ fontSize: 13 }}>this will permanently delete "{p.name}" and all associated cost data.</p>
            </div>
            <div className="dlg-ft">
              <Button onClick={() => setShowDel(false)} bracket>cancel</Button>
              <Button variant="danger" bracket onClick={handleDelete}>delete</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectDetailPage
