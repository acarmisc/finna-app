import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { Plus, RefreshCw } from 'lucide-react'

const CONNECTIONS = [
  {
    id:'ds1', name:'Azure · ACME Corp SRL', provider:'azure',
    type:'subscription', scope:'subscription',
    config:'acme-prod-azure', config_id:'cfg1',
    extractor:'azure_cost', schedule:'0 * * * *',
    last_run:{status:'completed', at:'Apr 23 09:14', records:2841},
    health:'healthy', records_total:'2.4M',
  },
  {
    id:'ds2', name:'GCP · my-gcp-project', provider:'gcp',
    type:'project', scope:'project',
    config:'gcp-production', config_id:'cfg2',
    extractor:'gcp_billing', schedule:'0 * * * *',
    last_run:{status:'running', at:'Apr 23 09:18', records:1284},
    health:'healthy', records_total:'890K',
  },
  {
    id:'ds3', name:'LLM · acme-openai-org', provider:'llm',
    type:'api', scope:'organization',
    config:'llm-gateway', config_id:'cfg3',
    extractor:'llm_usage', schedule:'0 6 * * *',
    last_run:{status:'failed', at:'Apr 22 14:30', records:0},
    health:'degraded', records_total:'142K',
  },
]

export function DataSourcesPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Data sources</h1>
          <div className="sub">// {CONNECTIONS.length} connections · 3.4M total records</div>
        </div>
        <div className="actions">
          <Button variant="outline" size="sm"><RefreshCw className="w-3 h-3"/>resync all</Button>
          <Button variant="default" size="sm"><Plus className="w-3 h-3"/>new source</Button>
        </div>
      </div>

      <div className="space-y-4">
        {CONNECTIONS.map(ds => (
          <Card key={ds.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <ProviderBadge provider={ds.provider} size="lg"/>
                  <div>
                    <CardTitle className="text-sm font-semibold text-foreground">{ds.name}</CardTitle>
                    <div className="font-mono text-[10px] text-muted-foreground mt-0.5">
                      {ds.type} · scope: {ds.scope} · config: <b>{ds.config}</b>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={ds.health==='healthy' ? 'ok' : ds.health==='degraded' ? 'pending' : 'failed'}/>
                  <div className="font-mono text-[10px] text-muted-foreground">{ds.records_total} records</div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4 text-xs">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">Extractor</div>
                  <div className="font-mono text-foreground">{ds.extractor}</div>
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">Schedule</div>
                  <div className="font-mono text-foreground">{ds.schedule}</div>
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">Last run</div>
                  <div className="flex items-center gap-1.5">
                    <StatusBadge status={ds.last_run.status}/>
                    <span className="font-mono text-[10px] text-muted-foreground">{ds.last_run.at}</span>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">Records extracted</div>
                  <div className="font-mono text-foreground tabular-nums">
                    {ds.last_run.records > 0 ? ds.last_run.records.toLocaleString() : '—'}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 mt-4 pt-3 border-t border-border">
                <Button size="sm" variant="outline">configure</Button>
                <Button size="sm" variant="outline">view logs</Button>
                <Button size="sm" variant="outline">trigger sync</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default DataSourcesPage
