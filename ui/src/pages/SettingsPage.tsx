import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { money } from '@/components/shared/money'

const SECTIONS = [
  {id:'profile',    label:'// profile'},
  {id:'notifications', label:'// notifications'},
  {id:'api-keys',   label:'// api keys'},
  {id:'appearance', label:'// appearance'},
  {id:'data',       label:'// data & retention'},
]

export function SettingsPage() {
  const [section, setSection] = useState('profile')
  const [saved, setSaved] = useState(false)
  const [profile, setProfile] = useState({
    name:'Andrea Carmisciano',
    email:'andrea@acme.co',
    timezone:'Europe/Rome',
    currency:'USD',
    date_format:'%b %d, %Y',
  })
  const [notif, setNotif] = useState({
    email_firing:true,  email_pending:false,
    telegram_firing:true, telegram_pending:true,
    slack_firing:false, slack_pending:false,
    telegram_chat_id:'@acme_finops',
    slack_webhook:'',
  })
  const [delDialog, setDelDialog] = useState(false)

  const save = () => {
    setSaved(true)
    setTimeout(()=>setSaved(false), 2000)
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <div className="sub">// user preferences · POST /api/v1/auth/profile</div>
        </div>
        <div className="actions">
          <Button size="sm" variant="default" onClick={save}>{saved ? '✓ saved' : 'save changes'}</Button>
        </div>
      </div>

      <div className="grid grid-cols-[200px_1fr] gap-6">
        {/* Side nav */}
        <div className="space-y-0.5">
          {SECTIONS.map(s => (
            <button
              key={s.id}
              onClick={()=>setSection(s.id)}
              className="w-full text-left px-3 py-2 font-mono text-xs transition-colors"
              style={{
                background: section===s.id ? 'var(--primary/10)' : 'transparent',
                color: section===s.id ? 'var(--primary)' : 'var(--fg-muted)',
                borderLeft: section===s.id ? '2px solid var(--primary)' : '2px solid transparent',
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div>
          {section==='profile' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">profile</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {([
                  {k:'name',        label:'full name'},
                  {k:'email',       label:'email address'},
                  {k:'timezone',    label:'timezone'},
                  {k:'currency',    label:'default currency'},
                  {k:'date_format', label:'date format'},
                ] as const).map(({k,label}) => (
                  <div key={k}>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">{label}</label>
                    <Input
                      className="font-mono text-xs max-w-sm"
                      value={(profile as any)[k]}
                      onChange={e=>setProfile(p=>({...p, [k]: e.target.value}))}
                    />
                  </div>
                ))}
                <div className="pt-2">
                  <Button size="sm" variant="outline" onClick={save}>{saved ? '✓' : 'save'}</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {section==='notifications' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">notification channels</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {([
                  {k:'email_firing',   label:'email · firing alerts'},
                  {k:'email_pending',  label:'email · pending alerts'},
                  {k:'telegram_firing',label:'telegram · firing alerts'},
                  {k:'telegram_pending',label:'telegram · pending alerts'},
                  {k:'slack_firing',   label:'slack · firing alerts'},
                  {k:'slack_pending',  label:'slack · pending alerts'},
                ] as const).map(({k,label}) => (
                  <div key={k} className="flex items-center justify-between">
                    <label className="text-sm text-foreground cursor-pointer">{label}</label>
                    <button
                      onClick={()=>setNotif(n=>({...n, [k]: !(n as any)[k]}))}
                      className="w-9 h-5 border border-border relative transition-colors"
                      style={{background: (notif as any)[k] ? 'var(--accent)' : 'var(--surface-2)'}}
                    >
                      <span className="absolute top-0.5 transition-all"
                        style={{[(notif as any)[k] ? 'left' : 'right']:'18px', color:'var(--bg)'}}>●</span>
                    </button>
                  </div>
                ))}
                <div className="border-t border-border pt-4 space-y-3">
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">telegram chat id</label>
                    <Input className="font-mono text-xs max-w-sm" value={notif.telegram_chat_id}
                      onChange={e=>setNotif(n=>({...n, telegram_chat_id: e.target.value}))}/>
                  </div>
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">slack webhook url</label>
                    <Input className="font-mono text-xs max-w-sm" value={notif.slack_webhook}
                      onChange={e=>setNotif(n=>({...n, slack_webhook: e.target.value}))}/>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {section==='api-keys' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">api keys</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  {name:'andrea-production', key:'sk_finna_prod_••••••••••••••••3f8a', created:'Jan 10, 2026', last:'2 hours ago', scopes:['read','write']},
                  {name:'ci-pipeline',       key:'sk_finna_ci_••••••••••••••••9c2d', created:'Feb 20, 2026', last:'1 day ago',    scopes:['read']},
                ].map(api => (
                  <div key={api.name} className="border border-border p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-foreground">{api.name}</span>
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline">regenerate</Button>
                        <Button size="sm" variant="ghost">revoke</Button>
                      </div>
                    </div>
                    <div className="font-mono text-[10px] text-muted-foreground">{api.key}</div>
                    <div className="flex gap-4 mt-2 text-[10px] font-mono text-muted-foreground">
                      <span>created {api.created}</span>
                      <span>last used {api.last}</span>
                      <span>scopes · {api.scopes.join(', ')}</span>
                    </div>
                  </div>
                ))}
                <Button size="sm" variant="outline" className="mt-2">+ new api key</Button>
              </CardContent>
            </Card>
          )}

          {section==='appearance' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">appearance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">theme</label>
                  <Select defaultValue="dark">
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dark">dark</SelectItem>
                      <SelectItem value="light">light</SelectItem>
                      <SelectItem value="system">system</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">date range picker</label>
                  <Select defaultValue="mtd">
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mtd">mtd · month to date</SelectItem>
                      <SelectItem value="7d">last 7d</SelectItem>
                      <SelectItem value="30d">last 30d</SelectItem>
                      <SelectItem value="90d">last 90d</SelectItem>
                      <SelectItem value="custom">custom range</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          )}

          {section==='data' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">data & retention</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="border border-border p-4">
                  <div className="text-sm font-semibold text-foreground mb-2">Raw cost records</div>
                  <div className="text-xs font-mono text-muted-foreground mb-3">retention · 90 days · 2.4M records · ~18 GB</div>
                  <Button size="sm" variant="outline">export csv</Button>
                </div>
                <div className="border border-border p-4">
                  <div className="text-sm font-semibold text-foreground mb-2">Enriched records</div>
                  <div className="text-xs font-mono text-muted-foreground mb-3">retention · 365 days · 890K records · ~7 GB</div>
                  <Button size="sm" variant="outline">export csv</Button>
                </div>
                <div className="border border-border p-4">
                  <div className="text-sm font-semibold text-danger mb-2">Danger zone</div>
                  <div className="text-xs font-mono text-muted-foreground mb-3">permanent deletion cannot be undone</div>
                  <Button size="sm" variant="destructive" onClick={()=>setDelDialog(true)}>delete all data</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={delDialog}
        onClose={()=>setDelDialog(false)}
        onConfirm={()=>setDelDialog(false)}
        title="Delete all data · IRREVERSIBLE"
        message="This will permanently delete all cost records, alerts, and run history. This action cannot be undone."
        variant="danger"
      />
    </div>
  )
}

export default SettingsPage
