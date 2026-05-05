import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { Search } from 'lucide-react'

const RUNS = [
  {run_id:'r_8f2c1a', extractor_type:'azure_cost', provider:'azure', status:'completed', records_extracted:2841, duration:'38s',  started_at:'Apr 23 09:14:22', finished_at:'Apr 23 09:15:00'},
  {run_id:'r_9a3d2b', extractor_type:'gcp_billing', provider:'gcp',   status:'running',   records_extracted:1284, duration:'—',     started_at:'Apr 23 09:18:05', finished_at:'—'},
  {run_id:'r_7b1e3c', extractor_type:'azure_cost', provider:'azure', status:'completed', records_extracted:3102, duration:'41s',  started_at:'Apr 22 14:30:11', finished_at:'Apr 22 14:30:52'},
  {run_id:'r_6c4f4d', extractor_type:'llm_usage',  provider:'llm',   status:'failed',    records_extracted:0,    duration:'—',     started_at:'Apr 22 08:00:00', finished_at:'Apr 22 08:00:01'},
  {run_id:'r_5d2g5e', extractor_type:'gcp_billing', provider:'gcp',   status:'completed', records_extracted:1920, duration:'29s',  started_at:'Apr 21 06:00:00', finished_at:'Apr 21 06:00:29'},
  {run_id:'r_4e3h6f', extractor_type:'azure_cost', provider:'azure', status:'completed', records_extracted:2750, duration:'35s',  started_at:'Apr 20 09:14:00', finished_at:'Apr 20 09:14:35'},
]

export function RunHistoryPage() {
  const [q, setQ] = useState('')
  const [provFilter, setProvFilter] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const rows = RUNS.filter(r =>
    (!q || r.run_id.includes(q) || r.extractor_type.includes(q)) &&
    (provFilter==='all' || r.provider===provFilter)
  )

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Extractor runs</h1>
          <div className="sub">// {rows.length} runs · cron: 0 * * * * (hourly) · next: in 41 min</div>
        </div>
        <div className="actions">
          <Button variant="outline" size="sm">trigger now</Button>
          <Button variant="outline" size="sm">export csv</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <div className="flex items-center gap-3">
            <div className="inp-group" style={{ maxWidth: 240 }}>
              <Input className="inp font-mono text-xs" placeholder="filter run id / extractor…"
                value={q} onChange={e=>setQ(e.target.value)}/>
            </div>
            <div className="flex gap-1">
              {['all','azure','gcp','llm'].map(p => (
                <button key={p} onClick={()=>setProvFilter(p)}
                  className="chip">
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="card-bd p0" style={{ maxHeight: 640, overflowY: 'auto' }}>
          <table className="tbl">
            <thead><tr>
              <th>Status</th><th>Run ID</th><th>Extractor</th><th>Provider</th>
              <th>Started</th><th>Finished</th><th className="num">Records</th><th className="num">Duration</th>
            </tr></thead>
            <tbody>
              {rows.map(r => (
                <React.Fragment key={r.run_id}>
                  <tr className="clickable" onClick={()=>setExpanded(e => e===r.run_id ? null : r.run_id)}>
                    <td><StatusBadge status={r.status}/></td>
                    <td><span className="id">{r.run_id}</span></td>
                    <td className="mono">{r.extractor_type}</td>
                    <td><ProviderBadge provider={r.provider}/></td>
                    <td className="mono muted">{r.started_at}</td>
                    <td className="mono muted">{r.finished_at || '—'}</td>
                    <td className="num mono">{r.records_extracted ? r.records_extracted.toLocaleString() : '—'}</td>
                    <td className="num mono">{r.duration}</td>
                  </tr>
                  {expanded === r.run_id && (
                    <tr>
                      <td colSpan={8} style={{ background: 'var(--bg)', padding: 16 }}>
                        <div className="row row-2">
                          <div>
                            <div className="label">run details</div>
                            <pre className="mono" style={{ fontSize: 11, margin: 0, background: 'var(--surface)', border: '1px solid var(--border)', padding: 10, color: 'var(--fg)' }}>{JSON.stringify({ run_id: r.run_id, extractor: r.extractor_type, provider: r.provider, status: r.status, records: r.records_extracted, duration: r.duration }, null, 2)}</pre>
                          </div>
                          <div>
                            <div className="label">error / stderr</div>
                            <div className="empty" style={{ padding: 16 }}><div className="msg">no errors</div></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default RunHistoryPage
