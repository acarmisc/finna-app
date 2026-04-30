import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { ProgressBar } from '@/components/shared/progress-bar'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'
import { money } from '@/components/shared/money'
import { useProjects } from '@/api/hooks'
import type { ProjectResponse } from '@/types/api'

const tagsToList = (tags?: ProjectResponse['tags']): string[] => {
  if (!tags) return []
  if (Array.isArray(tags)) return tags as string[]
  return Object.entries(tags).map(([k, v]) => v && v !== 'true' ? `${k}:${v}` : k)
}

export function ProjectsListPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const { data, isLoading, error } = useProjects()

  const projects = (data ?? []) as ProjectResponse[]
  const totalMtd = projects.reduce((s, p) => s + (p.mtd ?? 0), 0)

  const rows = projects.filter(p => {
    if (!q) return true
    const tagList = tagsToList(p.tags)
    return p.name.toLowerCase().includes(q.toLowerCase())
      || (p.owner ?? '').toLowerCase().includes(q.toLowerCase())
      || (p.slug ?? '').toLowerCase().includes(q.toLowerCase())
      || tagList.some(t => t.toLowerCase().includes(q.toLowerCase()))
  })

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Projects</h1>
          <div className="sub">// {rows.length} projects · {money(totalMtd)} MTD {error && <span style={{ color: 'var(--danger)' }}>· api unreachable</span>}</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket onClick={() => navigate('/projects/new')}>new project</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <div className="hstack-3" style={{ flex: 1 }}>
            <div className="inp-group" style={{ maxWidth: 360, width: '100%' }}>
              <Icon name="search" size={14} />
              <input className="inp" placeholder="filter name / owner / tag…" value={q} onChange={e => setQ(e.target.value)} />
            </div>
            <span className="chip">provider: <b>any</b></span>
            <span className="chip">budget: <b>all</b></span>
          </div>
          <span className="muted mono" style={{ fontSize: 11 }}>sorted by · MTD desc</span>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>Name</th><th>Slug</th><th>Owner</th><th>Cost center</th>
              <th className="num">Budget cap</th><th className="num">MTD</th>
              <th>Budget used</th><th>Tags</th>
            </tr></thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={8} className="muted" style={{ textAlign: 'center', padding: 24 }}>// loading projects…</td></tr>
              )}
              {[...rows].sort((a, b) => (b.mtd ?? 0) - (a.mtd ?? 0)).map(p => {
                const cap = p.budget_cap ?? 0
                const mtd = p.mtd ?? 0
                const pct = cap > 0 ? (mtd / cap) * 100 : 0
                const tags = tagsToList(p.tags)
                return (
                  <tr key={p.id} className="clickable" onClick={() => navigate(`/projects/${p.slug ?? p.id}`)}>
                    <td>
                      <span className="hstack">
                        {p.provider && <ProviderBadge provider={p.provider} />}
                        <b style={{ fontWeight: 500 }}>{p.name}</b>
                      </span>
                    </td>
                    <td className="mono muted">{p.slug ?? '—'}</td>
                    <td>{p.owner ?? '—'}</td>
                    <td className="mono">{p.cost_center ?? '—'}</td>
                    <td className="num mono">{cap ? money(cap, 0) : '—'}</td>
                    <td className="num mono">{money(mtd)}</td>
                    <td style={{ minWidth: 160 }}>
                      <div className="hstack-3" style={{ gap: 10 }}>
                        <div style={{ flex: 1 }}><ProgressBar value={mtd} max={Math.max(cap, 1)} /></div>
                        <span className="mono num" style={{ fontSize: 11, minWidth: 40, textAlign: 'right', color: pct >= 90 ? 'var(--danger)' : pct >= 70 ? 'var(--warning)' : 'var(--fg-muted)' }}>{cap ? `${pct.toFixed(0)}%` : '—'}</span>
                      </div>
                    </td>
                    <td>{tags.map(t => <span key={t} className="chip" style={{ marginRight: 4 }}>{t}</span>)}</td>
                  </tr>
                )
              })}
              {!isLoading && rows.length === 0 && (
                <tr><td colSpan={8} style={{ padding: 0 }}>
                  <EmptyState icon="folders" title={projects.length === 0 ? 'No projects' : 'No matches'} message={projects.length === 0 ? 'no projects in database' : `no projects match "${q}"`} />
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default ProjectsListPage
