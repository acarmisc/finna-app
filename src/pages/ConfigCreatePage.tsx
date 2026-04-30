import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ProviderBadge } from '@/components/shared/provider-badge'
import { ArrowLeft } from 'lucide-react'

export function ConfigCreatePage() {
  const [step, setStep] = useState(1)
  const [prov, setProv] = useState<'azure'|'gcp'|null>(null)
  const [cred, setCred] = useState('service_principal')
  const [fields, setFields] = useState({
    name:'', tenant_id:'', client_id:'', client_secret:'',
    subscription_id:'', project_id:'', key_file:'',
  })

  const set = (k: string, v: string) => setFields(f => ({...f, [k]:v}))

  const canNext =
    (step===1 && prov) ||
    (step===2 && (
      prov==='azure'
        ? (cred==='service_principal'
            ? (fields.name && fields.tenant_id && fields.client_id && fields.client_secret && fields.subscription_id)
            : (fields.name && fields.subscription_id))
        : (fields.name && fields.project_id && (cred!=='service_principal' || fields.key_file))
    )) ||
    step===3

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <Link to="/configs" className="font-mono text-[11px] text-muted-foreground hover:text-foreground">
            ← configs
          </Link>
          <h1 style={{marginTop:6}}>New cloud config</h1>
          <div className="sub">// 3-step setup · POST /api/v1/config</div>
        </div>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-3 mb-6 font-mono text-xs">
        {[
          {n:1, label:'provider'},
          {n:2, label:'credentials'},
          {n:3, label:'review'},
        ].map(({n,label}, i, arr) => (
          <React.Fragment key={n}>
            <div className="flex items-center gap-1.5">
              <span className={`w-5 h-5 flex items-center justify-center border text-[10px] ${
                step>n ? 'border-accent bg-accent/10 text-accent' :
                step===n ? 'border-primary bg-primary/10 text-primary' :
                'border-border text-muted-foreground'
              }`}>
                {step>n ? '✓' : n}
              </span>
              <span className={step>=n ? 'text-foreground' : 'text-muted-foreground'}>{label}</span>
            </div>
            {i < arr.length-1 && <span className="text-muted-foreground">→</span>}
          </React.Fragment>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {step===1 && (
            <div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">select a provider</div>
              <div className="grid grid-cols-2 gap-4">
                {([
                  {id:'azure', title:'Microsoft Azure', desc:'Cost Management export · subscription or RG scope', color:'var(--azure)'},
                  {id:'gcp',   title:'Google Cloud',    desc:'BigQuery billing export · project scope',         color:'var(--gcp)'},
                ] as const).map(p => (
                  <button
                    key={p.id}
                    onClick={()=>setProv(p.id)}
                    className="p-5 text-left border cursor-pointer transition-all"
                    style={{
                      background: prov===p.id ? `color-mix(in oklch, ${p.color} 10%, var(--surface))` : 'var(--surface)',
                      borderColor: prov===p.id ? p.color : 'var(--border)',
                      boxShadow: prov===p.id ? `inset 0 0 0 1px ${p.color}` : 'none',
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <ProviderBadge provider={p.id} size="lg"/>
                      {prov===p.id && (
                        <span className="font-mono text-[10px] uppercase tracking-wider" style={{color:p.color}}>✓ selected</span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-foreground">{p.title}</div>
                    <div className="font-mono text-[10px] text-muted-foreground mt-1">{p.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

           {step===2 && prov==='azure' && (
             <div className="space-y-4">
               <div>
                 <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">credential type</label>
                 <Select value={cred} onValueChange={(v: string | null)=>setCred(v || "service_principal")}>
                  <SelectTrigger className="font-mono text-xs"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="service_principal">service_principal</SelectItem>
                    <SelectItem value="managed_identity">managed_identity</SelectItem>
                    <SelectItem value="cli">cli</SelectItem>
                    <SelectItem value="device_code">device_code</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">name *</label>
                <Input className="font-mono text-xs" placeholder="acme-prod-azure" value={fields.name} onChange={e=>set('name',e.target.value)}/>
              </div>
              {cred==='service_principal' && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">tenant id *</label>
                      <Input className="font-mono text-xs" placeholder="8f2c-…-a1e9" value={fields.tenant_id} onChange={e=>set('tenant_id',e.target.value)}/>
                    </div>
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">client secret *</label>
                      <Input type="password" className="font-mono text-xs" value={fields.client_secret} onChange={e=>set('client_secret',e.target.value)}/>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">client id *</label>
                    <Input className="font-mono text-xs" value={fields.client_id} onChange={e=>set('client_id',e.target.value)}/>
                  </div>
                </>
              )}
              <div>
                <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">subscription id *</label>
                <Input className="font-mono text-xs" placeholder="00000000-0000-0000-…" value={fields.subscription_id} onChange={e=>set('subscription_id',e.target.value)}/>
              </div>
            </div>
          )}

           {step===2 && prov==='gcp' && (
             <div className="space-y-4">
               <div>
                 <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">credential type</label>
                 <Select value={cred} onValueChange={(v: string | null)=>setCred(v || "service_principal")}>
                  <SelectTrigger className="font-mono text-xs"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="service_principal">service account key</SelectItem>
                    <SelectItem value="cli">cli (gcloud adc)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">name *</label>
                <Input className="font-mono text-xs" placeholder="prod-platform-gcp" value={fields.name} onChange={e=>set('name',e.target.value)}/>
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">project id *</label>
                <Input className="font-mono text-xs" placeholder="acme-prod-platform" value={fields.project_id} onChange={e=>set('project_id',e.target.value)}/>
              </div>
              {cred==='service_principal' && (
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">service account key (JSON) *</label>
                  <div className="border border-dashed border-border p-4 bg-background text-center font-mono text-[11px] text-muted-foreground">
                    <div className="mb-2">drop key.json here or click to browse</div>
                    <Button size="sm" variant="outline" onClick={()=>set('key_file','sa-acme-prod.json')}>browse</Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {step===3 && (
            <div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">review</div>
              <div className="border border-border bg-background p-4 font-mono text-xs">
                <div className="text-[10px] text-muted-foreground mb-2"># POST /api/v1/config</div>
                <pre className="text-foreground whitespace-pre-wrap leading-relaxed">{JSON.stringify({
                  name: fields.name, provider: prov, credential_type: cred,
                  ...(prov==='azure' ? {
                    tenant_id: fields.tenant_id || '(unset)',
                    client_id: fields.client_id || '(unset)',
                    client_secret: fields.client_secret ? '••••••••' : '(unset)',
                    subscription_id: fields.subscription_id,
                  } : {
                    project_id: fields.project_id,
                    key_file: fields.key_file || '(unset)',
                  })
                }, null, 2)}</pre>
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-3">// secrets are encrypted at rest · stored in cloud_config table</div>
            </div>
          )}
        </CardContent>
        <div className="px-4 py-3 border-t border-border flex justify-between">
          <Button size="sm" variant="outline" disabled={step===1} onClick={()=>setStep(s=>Math.max(1,s-1))}>← back</Button>
          {step < 3 ? (
            <Button size="sm" variant="default" disabled={!canNext} onClick={()=>setStep(s=>s+1)}>next step →</Button>
          ) : (
            <Button size="sm" variant="default">create config</Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export default ConfigCreatePage
