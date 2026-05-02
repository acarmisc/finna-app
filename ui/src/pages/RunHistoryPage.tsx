import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted-foreground"/>
              <Input className="pl-8 font-mono text-xs" placeholder="filter run id / extractor…"
                value={q} onChange={e=>setQ(e.target.value)}/>
            </div>
            <div className="flex gap-1">
              {['all','azure','gcp','llm'].map(p => (
                <button key={p} onClick={()=>setProvFilter(p)}
                  className="px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider border transition-colors"
                  style={{
                    background: provFilter===p ? 'var(--primary/10)' : 'transparent',
                    borderColor: provFilter===p ? 'var(--primary)' : 'var(--border)',
                    color: provFilter===p ? 'var(--primary)' : 'var(--fg-muted)',
                  }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-alt">
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Provider</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Extractor</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Status</th>
                  <th className="text-right px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Records</th>
                  <th className="text-right px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Duration</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Started</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Finished</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Run ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map(r => (
                  <tr key={r.run_id} className="hover:bg-surface-alt transition-colors cursor-pointer">
                    <td className="px-4 py-2"><ProviderBadge provider={r.provider}/></td>
                    <td className="px-4 py-2 font-mono text-xs text-foreground">{r.extractor_type}</td>
                    <td className="px-4 py-2"><StatusBadge status={r.status}/></td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-foreground tabular-nums">
                      {r.records_extracted > 0 ? r.records_extracted.toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs text-muted-foreground tabular-nums">{r.duration}</td>
                    <td className="px-4 py-2 font-mono text-[10px] text-foreground">{r.started_at}</td>
                    <td className="px-4 py-2 font-mono text-[10px] text-muted-foreground">{r.finished_at}</td>
                    <td className="px-4 py-2 font-mono text-[10px] text-muted-foreground">{r.run_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default RunHistoryPage
