import React, { useState } from 'react'
import { StatCard } from '@/components/shared/stat-card'
import { LineChart } from '@/components/shared/line-chart'
import { HBarList } from '@/components/shared/hbar-list'
import { StatusBadge } from '@/components/shared/status-badge'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { money } from '@/components/shared/money'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/services/apiClient'

// richer mock data
const MOCK = {
  totals: {
    total: { mtd: 2590.75, delta: 12.4 },
    azure: { mtd: 1250.50, delta: 8.2 },
    gcp:   { mtd: 890.25,  delta: 15.1 },
    llm:   { mtd: 450.00,  delta: 22.3 },
  },
  daily: {
    azure: [
      {label:'Apr 1',value:38},{label:'Apr 3',value:42},{label:'Apr 5',value:41},
      {label:'Apr 7',value:45},{label:'Apr 9',value:52},{label:'Apr 11',value:48},
      {label:'Apr 13',value:55},{label:'Apr 15',value:50},{label:'Apr 17',value:58},
      {label:'Apr 19',value:54},{label:'Apr 21',value:62},{label:'Apr 23',value:60},
    ],
    gcp: [
      {label:'Apr 1',value:22},{label:'Apr 3',value:25},{label:'Apr 5',value:24},
      {label:'Apr 7',value:28},{label:'Apr 9',value:30},{label:'Apr 11',value:27},
      {label:'Apr 13',value:32},{label:'Apr 15',value:29},{label:'Apr 17',value:35},
      {label:'Apr 19',value:33},{label:'Apr 21',value:38},{label:'Apr 23',value:36},
    ],
    llm: [
      {label:'Apr 1',value:12},{label:'Apr 3',value:14},{label:'Apr 5',value:13},
      {label:'Apr 7',value:16},{label:'Apr 9',value:18},{label:'Apr 11',value:15},
      {label:'Apr 13',value:20},{label:'Apr 15',value:17},{label:'Apr 17',value:22},
      {label:'Apr 19',value:19},{label:'Apr 21',value:24},{label:'Apr 23',value:21},
    ],
  },
  projects: [
    {id:'p1', name:'production', slug:'production', provider:'azure', owner:'alice@acme.co', cost_center:'ENG-001', budget_cap:5000, mtd:3210.50, tags:['prod','critical']},
    {id:'p2', name:'staging',    slug:'staging',    provider:'gcp',   owner:'bob@acme.co',   cost_center:'ENG-002', budget_cap:2000, mtd:890.25,  tags:['staging']},
    {id:'p3', name:'ml-platform',slug:'ml-platform',provider:'llm',   owner:'carol@acme.co', cost_center:'ML-001',  budget_cap:1500, mtd:1240.00, tags:['ml','internal']},
    {id:'p4', name:'dev-sandbox',slug:'dev-sandbox',provider:'azure', owner:'dave@acme.co',  cost_center:'ENG-003', budget_cap:500,  mtd:145.00,  tags:['dev']},
  ],
  runs: [
    {run_id:'r_8f2c1a', extractor_type:'azure_cost', provider:'azure', status:'completed', records_extracted:2841, duration:'38s',  started_at:'Apr 23 09:14'},
    {run_id:'r_9a3d2b', extractor_type:'gcp_billing', provider:'gcp',   status:'running',   records_extracted:1284, duration:'—',     started_at:'Apr 23 09:18'},
    {run_id:'r_7b1e3c', extractor_type:'azure_cost', provider:'azure', status:'completed', records_extracted:3102, duration:'41s',  started_at:'Apr 22 14:30'},
    {run_id:'r_6c4f4d', extractor_type:'llm_usage',  provider:'llm',   status:'failed',    records_extracted:0,    duration:'—',     started_at:'Apr 22 08:00'},
    {run_id:'r_5d2g5e', extractor_type:'gcp_billing', provider:'gcp',   status:'completed', records_extracted:1920, duration:'29s',  started_at:'Apr 21 06:00'},
  ],
}

const RANGE_LABELS: Record<string,string> = { mtd:'MTD','7d':'last 7d','30d':'last 30d','90d':'last 90d' }

export function DashboardPage({ range='mtd' }: { range?: string }) {
  const [editMode, setEditMode] = useState(false)
  const scale: Record<string,number> = { mtd:1,'7d':0.23,'30d':1.05,'90d':3.08 }
  const s = scale[range] ?? 1
  const rl = RANGE_LABELS[range] ?? 'MTD'

  const chartSeries = [
    { name:'Azure', color:'var(--azure)', data: MOCK.daily.azure.map(d=>({label:d.label, value:+(d.value*s).toFixed(2)})) },
    { name:'GCP',   color:'var(--gcp)',   data: MOCK.daily.gcp.map(d=>({label:d.label, value:+(d.value*s).toFixed(2)})) },
    { name:'LLM',   color:'var(--llm)',   data: MOCK.daily.llm.map(d=>({label:d.label, value:+(d.value*s).toFixed(2)})) },
  ]

  const topProjects = [...MOCK.projects].sort((a,b)=>b.mtd-a.mtd).slice(0,5).map(p=>({
    ...p, value: +(p.mtd*s).toFixed(2),
  }))

  const llmBreakdown = [
    {name:'Claude Sonnet', value:+(MOCK.totals.llm.mtd*s*0.58).toFixed(2), tokens:'4.2M in · 1.8M out'},
    {name:'GPT-4o',         value:+(MOCK.totals.llm.mtd*s*0.31).toFixed(2), tokens:'2.1M in · 0.9M out'},
    {name:'Embeddings',     value:+(MOCK.totals.llm.mtd*s*0.08).toFixed(2), tokens:'12.4M'},
    {name:'Haiku',         value:+(MOCK.totals.llm.mtd*s*0.03).toFixed(2), tokens:'620K in · 180K out'},
  ]
  const llmTotal = llmBreakdown.reduce((a,x)=>a+x.value, 0)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <div className="sub">// last refresh · 4 min ago · all sources healthy · window: {rl}</div>
        </div>
        <div className="actions">
          <Button variant="outline" size="sm" onClick={()=>setEditMode(m=>!m)}>
            {editMode ? 'done' : 'customize'}
          </Button>
          <Button variant="outline" size="sm">refresh</Button>
          <Button variant="outline" size="sm">export</Button>
        </div>
      </div>

      {/* KPI row */}
      <div className="row row-4" style={{marginBottom:16}}>
        <StatCard
          label={`Total ${rl}`}
          value={money(MOCK.totals.total.mtd * s)}
          delta={`+${(MOCK.totals.total.delta*s).toFixed(1)}%`}
          deltaDir="up"
          meta="vs last month"
          accent="primary"
        />
        <StatCard
          label={`Azure ${rl}`}
          value={money(MOCK.totals.azure.mtd * s)}
          delta={`+${MOCK.totals.azure.delta}%`}
          deltaDir="up"
          meta="3 subscriptions"
          accent="azure"
        />
        <StatCard
          label={`GCP ${rl}`}
          value={money(MOCK.totals.gcp.mtd * s)}
          delta={`+${MOCK.totals.gcp.delta}%`}
          deltaDir="up"
          meta="2 projects"
          accent="gcp"
        />
        <StatCard
          label={`LLM ${rl}`}
          value={money(MOCK.totals.llm.mtd * s)}
          delta={`+${MOCK.totals.llm.delta}%`}
          deltaDir="up"
          meta="3 models"
          accent="llm"
        />
      </div>

      {/* Cost trend + top projects */}
      <div className="row" style={{gridTemplateColumns:'1fr 360px', gap:16, marginBottom:16}}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              Daily cost · {rl}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart series={chartSeries} height={260} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              Top projects · {rl}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <HBarList
              items={topProjects.map(p=>({ name:p.name, value:p.value, provider:p.provider }))}
              max={topProjects[0]?.value}
            />
          </CardContent>
        </Card>
      </div>

      {/* LLM spend + recent runs */}
      <div className="row" style={{gridTemplateColumns:'380px 1fr', gap:16}}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              LLM spend by model · {rl}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {llmBreakdown.map(m => {
              const pct = Math.round((m.value/llmTotal)*100)
              return (
                <div key={m.name}>
                  <div className="flex justify-between items-baseline mb-1">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 inline-block" style={{background:'var(--llm)'}}/>
                      <span className="text-sm text-foreground">{m.name}</span>
                      <span className="font-mono text-[10px] text-muted-foreground">{m.tokens}</span>
                    </div>
                    <div className="font-mono text-sm">
                      <span>{money(m.value)}</span>
                      <span className="text-muted-foreground ml-2">{pct}%</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-surface-2 border border-border">
                    <div className="h-full" style={{width:`${pct}%`, background:'var(--llm)'}}/>
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              Recent extractor runs
            </CardTitle>
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
                    <th className="text-left px-4 py-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground font-normal">Run ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {MOCK.runs.map(r => (
                    <tr key={r.run_id} className="hover:bg-surface-alt transition-colors">
                      <td className="px-4 py-2"><ProviderBadge provider={r.provider}/></td>
                      <td className="px-4 py-2 font-mono text-xs text-foreground">{r.extractor_type}</td>
                      <td className="px-4 py-2"><StatusBadge status={r.status}/></td>
                      <td className="px-4 py-2 text-right font-mono text-xs text-foreground tabular-nums">
                        {r.records_extracted > 0 ? r.records_extracted.toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-xs text-muted-foreground tabular-nums">{r.duration}</td>
                      <td className="px-4 py-2 font-mono text-[10px] text-muted-foreground">{r.run_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage
