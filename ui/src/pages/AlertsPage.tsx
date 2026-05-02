import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBadge } from '@/components/shared/status-badge'
import { money } from '@/components/shared/money'
import { Plus, Bell, Search } from 'lucide-react'

const ALERTS = [
  {id:'a1', name:'production · budget 80%',     target_type:'project',     target_name:'production',    metric:'budget_utilization', condition:'>', threshold:80, current_value:81.2, status:'firing',   provider:'azure', created_at:'Mar 15'},
  {id:'a2', name:'production · spike > 500',    target_type:'project',     target_name:'production',    metric:'daily_cost',          condition:'>', threshold:500, current_value:623, status:'firing',   provider:'azure', created_at:'Mar 18'},
  {id:'a3', name:'staging · budget 80%',        target_type:'project',     target_name:'staging',       metric:'budget_utilization', condition:'>', threshold:80, current_value:44.5, status:'ok',      provider:'gcp',   created_at:'Mar 20'},
  {id:'a4', name:'GCP · API errors > 100/h',    target_type:'provider',     target_name:'gcp',           metric:'error_rate',         condition:'>', threshold:100, current_value:12,  status:'ok',      provider:'gcp',   created_at:'Mar 22'},
  {id:'a5', name:'LLM · cost > 200/day',        target_type:'project',     target_name:'ml-platform',   metric:'daily_cost',         condition:'>', threshold:200, current_value:187, status:'pending',  provider:'llm',   created_at:'Apr 1'},
  {id:'a6', name:'Azure · idle resources',       target_type:'provider',     target_name:'azure',         metric:'idle_resources',      condition:'>', threshold:5,   current_value:9,   status:'firing',   provider:'azure', created_at:'Apr 5'},
]

const STATS = {
  total: ALERTS.length,
  firing: ALERTS.filter(a=>a.status==='firing').length,
  pending: ALERTS.filter(a=>a.status==='pending').length,
  resolved: ALERTS.filter(a=>a.status==='ok').length,
}

export function AlertsPage() {
  const [q, setQ] = useState('')
  const rows = ALERTS.filter(a =>
    !q || a.name.includes(q) || a.target_name.includes(q) || a.provider.includes(q)
  )

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Alerts</h1>
          <div className="sub">// {STATS.firing} firing · {STATS.pending} pending · {STATS.resolved} resolved · last 90 days</div>
        </div>
        <div className="actions">
          <Button variant="default" size="sm"><Plus className="w-3 h-3"/>new alert</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        {[
          {label:'Total', value:STATS.total, color:'var(--fg-muted)'},
          {label:'Firing', value:STATS.firing, color:'var(--danger)'},
          {label:'Pending', value:STATS.pending, color:'var(--warning)'},
          {label:'Resolved', value:STATS.resolved, color:'var(--accent)'},
        ].map(s => (
          <Card key={s.label}>
            <CardContent className="pt-4 pb-3">
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">{s.label}</div>
              <div className="text-2xl font-mono font-semibold" style={{color:s.color}}>{s.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">All alerts</CardTitle>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted-foreground"/>
              <Input className="pl-8 font-mono text-xs w-52" placeholder="filter…" value={q} onChange={e=>setQ(e.target.value)}/>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-alt">
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Status</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Name</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Condition</th>
                  <th className="text-right px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Current</th>
                  <th className="text-right px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Threshold</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Provider</th>
                  <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map(a => (
                  <tr key={a.id} className="hover:bg-surface-alt transition-colors cursor-pointer">
                    <td className="px-4 py-3"><StatusBadge status={a.status}/></td>
                    <td className="px-4 py-3 text-sm text-foreground">{a.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                      {a.metric} {a.condition} {a.threshold}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs tabular-nums"
                      style={{color: a.status==='firing' ? 'var(--danger)' : 'var(--foreground)'}}>
                      {typeof a.current_value === 'number' && a.current_value > 1000
                        ? money(a.current_value)
                        : a.current_value.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground tabular-nums">{a.threshold}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground uppercase">{a.provider}</td>
                    <td className="px-4 py-3 font-mono text-[10px] text-muted-foreground">{a.created_at}</td>
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

export default AlertsPage
