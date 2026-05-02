import React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// Mini bar chart component for dashboard
function MiniBarChart({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data, 1)
  return (
    <div className="flex items-end gap-1 h-16">
      {data.map((v, i) => (
        <div key={i} className="flex-1 rounded-sm transition-all" style={{ width: `${v / (max || 1) * 100}%`, background: color }} />
      ))}
    </div>
  )
}

export function Dashboard() {
  // Mock data - would come from hooks in real implementation
  const totals = {
    totals: { azure: 1250.50, gcp: 890.25, llm: 450.00 },
    startDate: '2026-04-01',
    endDate: '2026-04-30'
  }
  const daily = {
    days: [
      { date: '2026-04-20', azure: 50, gcp: 30, llm: 20 },
      { date: '2026-04-21', azure: 55, gcp: 35, llm: 25 },
      { date: '2026-04-22', azure: 48, gcp: 32, llm: 18 },
    ],
    startDate: '2026-04-01',
    endDate: '2026-04-30'
  }
  const alertStats = {
    total: 15,
    pending: 8,
    by_severity: { err: 5, warn: 7, ok: 3 },
    acknowledged: 7
  }
  const projects = [
    { id: '1', name: 'Production Project', owner: 'alice@example.com', cost_center: ' eng', mtd: 1250.50, budget_cap: 5000 },
    { id: '2', name: 'Staging Project', owner: 'bob@example.com', cost_center: 'eng', mtd: 250.25, budget_cap: 2000 },
    { id: '3', name: 'Dev Project', owner: 'charlie@example.com', cost_center: 'eng', mtd: 450.00, budget_cap: 3000 },
  ]
  
  const dailyAzure = (daily.days || []).map((d: any) => d.azure || 0).reverse()
  const dailyGcp = (daily.days || []).map((d: any) => d.gcp || 0).reverse()
  const dailyLlm = (daily.days || []).map((d: any) => d.llm || 0).reverse()

  const totalCost = Object.entries(totals.totals || {}).reduce((acc, [, val]) => acc + (val as number), 0)

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <Badge variant="outline" className="text-sm">Last 30 days</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-slate-800 border-slate-700">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Total Cost</div>
          <div className="text-2xl font-bold text-blue-400">${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </Card>
        <Card className="p-4 bg-slate-800 border-slate-700">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Providers</div>
          <div className="text-2xl font-bold text-green-400">{Object.keys(totals.totals || {}).length}</div>
        </Card>
        <Card className="p-4 bg-slate-800 border-slate-700">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Active Alerts</div>
          <div className="text-2xl font-bold text-red-400">{alertStats.pending}</div>
        </Card>
        <Card className="p-4 bg-slate-800 border-slate-700">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Projects</div>
          <div className="text-2xl font-bold text-purple-400">{projects.length}</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Cost by Provider</h3>
            <div className="space-y-3">
              {Object.entries(totals.totals || {} as Record<string, number>).map(([prov, val]) => (
                <div key={prov} className="flex items-center gap-3">
                  <span className="w-16 text-xs font-medium uppercase text-slate-400">{prov}</span>
                  <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${(val as number) / (totalCost || 1) * 100}%`, background: prov === 'azure' ? '#2563eb' : prov === 'gcp' ? '#059669' : '#dc2626' }} />
                  </div>
                  <span className="w-20 text-right text-sm text-white font-medium">${(val as number).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Daily Trend</h3>
            <div className="space-y-2">
              {dailyAzure.length > 0 && <MiniBarChart data={dailyAzure} color="#2563eb" />}
              {dailyGcp.length > 0 && <MiniBarChart data={dailyGcp} color="#059669" />}
              {dailyLlm.length > 0 && <MiniBarChart data={dailyLlm} color="#dc2626" />}
            </div>
            <div className="flex gap-4 mt-4 text-xs text-slate-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> Azure</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" /> GCP</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> LLM</span>
            </div>
          </div>
        </Card>
      </div>

      <Card className="bg-slate-800 border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300">Projects</h3>
          <span className="text-xs text-slate-500">{projects.length} items</span>
        </div>
        <div className="divide-y divide-slate-700">
          {projects.map((p: any) => (
            <div key={p.id} className="px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors">
              <div>
                <div className="text-sm font-medium text-white">{p.name}</div>
                <div className="text-xs text-slate-400">{p.owner} · {p.cost_center}</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-white">${(p.mtd ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                <div className="text-xs text-slate-400">of ${(p.budget_cap ?? 0).toLocaleString()}</div>
              </div>
            </div>
          ))}
          {!projects.length && <div className="px-4 py-6 text-center text-slate-500 text-sm">No projects found</div>}
        </div>
      </Card>
    </div>
  )
}

export function Projects() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Projects</h1>
        <Button>Create Project</Button>
      </div>
      <Card className="bg-slate-800 border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300">Projects</h3>
        </div>
        <div className="divide-y divide-slate-700">
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors">
              <div>
                <div className="text-sm font-medium text-white">Project {i}</div>
                <div className="text-xs text-slate-400">owner@example.com</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export function Costs() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Cost Explorer</h1>
        <div className="flex gap-2">
          <Button variant="outline">Filter</Button>
          <Button variant="outline">Export</Button>
        </div>
      </div>
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sku">By SKU</TabsTrigger>
          <TabsTrigger value="daily">Daily Trend</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="animate-in fade-in duration-300">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-4 bg-slate-800 border-slate-700">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Total Cost</div>
              <div className="text-2xl font-bold text-white">$2,590.75</div>
            </Card>
            <Card className="p-4 bg-slate-800 border-slate-700">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Azure</div>
              <div className="text-2xl font-bold text-blue-400">$1,250.50</div>
            </Card>
            <Card className="p-4 bg-slate-800 border-slate-700">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">GCP</div>
              <div className="text-2xl font-bold text-green-400">$890.25</div>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="sku">
          <div className="text-center py-8 text-slate-400">SKU breakdown coming soon</div>
        </TabsContent>
        <TabsContent value="daily">
          <div className="text-center py-8 text-slate-400">Daily trend chart coming soon</div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export function Alerts() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Alerts</h1>
        <div className="flex gap-2">
          <Badge variant="outline" className="text-sm">Total: 15</Badge>
          <Badge variant="destructive" className="text-sm">Firing: 8</Badge>
          <Badge className="text-sm bg-green-500 text-white">Resolved: 7</Badge>
        </div>
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="bg-slate-800 border-slate-700 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-red-500/20 text-red-300">err</span>
                </div>
                <h3 className="text-sm font-semibold text-white">高 Priority Alert {i}</h3>
                <p className="text-sm text-slate-400 mt-1">This is a simulated alert description for testing purposes.</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function Configs() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Configurations</h1>
        <Button>Add Configuration</Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Cloud Connections</h2>
          <Card className="bg-slate-800 border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">Connections</h3>
            </div>
            <div className="divide-y divide-slate-700">
              {[1, 2].map((i) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors">
                  <div>
                    <div className="text-sm font-medium text-white">Connection {i}</div>
                    <div className="text-xs text-slate-400">{i === 1 ? 'azure' : 'gcp'}</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Projects</h2>
          <Card className="bg-slate-800 border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">Projects</h3>
            </div>
            <div className="divide-y divide-slate-700">
              {[1, 2, 3].map((i) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between hover:bg-slate-750 transition-colors">
                  <div>
                    <div className="text-sm font-medium text-white">Project {i}</div>
                    <div className="text-xs text-slate-400">owner@example.com</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
