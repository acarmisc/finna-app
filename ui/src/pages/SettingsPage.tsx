import React, { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'

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
          <Button size="sm" variant="primary" bracket onClick={save}>{saved ? '✓ saved' : 'save changes'}</Button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 12 }}>
        {/* Side nav */}
        <div className="card" style={{ alignSelf: 'start', height: 'fit-content' }}>
          <div className="card-bd stack stack-1">
            {SECTIONS.map(s => (
              <button
                key={s.id}
                onClick={()=>setSection(s.id)}
                className="chip"
                style={{
                  textAlign: 'left',
                  background: section===s.id ? 'var(--primary)' : 'var(--surface)',
                  color: section===s.id ? 'var(--primary-fg)' : 'var(--fg)',
                  cursor: 'pointer',
                  border: 'none',
                  padding: '8px 12px',
                  fontSize: 12,
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div>
          {section==='profile' && (
            <div className="card">
              <div className="card-hd"><h3>profile</h3></div>
              <div className="card-bd stack stack-4">
                {([
                  {k:'name',        label:'full name'},
                  {k:'email',       label:'email address'},
                  {k:'timezone',    label:'timezone'},
                  {k:'currency',    label:'default currency'},
                  {k:'date_format', label:'date format'},
                ] as const).map(({k,label}) => (
                  <div key={k}>
                    <div className="label">{label}</div>
                    <input
                      className="inp"
                      value={(profile as any)[k]}
                      onChange={e=>setProfile(p=>({...p, [k]: e.target.value}))}
                    />
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                  <Button size="sm" bracket onClick={save}>{saved ? '✓ saved' : 'save'}</Button>
                </div>
              </div>
            </div>
          )}

          {section==='notifications' && (
            <div className="card">
              <div className="card-hd"><h3>notification channels</h3></div>
              <div className="card-bd stack stack-3">
                {([
                  {k:'email_firing',   label:'email · firing alerts'},
                  {k:'email_pending',  label:'email · pending alerts'},
                  {k:'telegram_firing',label:'telegram · firing alerts'},
                  {k:'telegram_pending',label:'telegram · pending alerts'},
                  {k:'slack_firing',   label:'slack · firing alerts'},
                  {k:'slack_pending',  label:'slack · pending alerts'},
                ] as const).map(({k,label}) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <label style={{ cursor: 'pointer', fontSize: 12 }}>{label}</label>
                    <input
                      type="checkbox"
                      checked={(notif as any)[k]}
                      onChange={e=>setNotif(n=>({...n, [k]: e.target.checked}))}
                      style={{ cursor: 'pointer', width: 18, height: 18 }}
                    />
                  </div>
                ))}
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, marginTop: 12 }}>
                  <div className="stack stack-3">
                    <div>
                      <div className="label">telegram chat id</div>
                      <input className="inp" value={notif.telegram_chat_id}
                        onChange={e=>setNotif(n=>({...n, telegram_chat_id: e.target.value}))}/>
                    </div>
                    <div>
                      <div className="label">slack webhook url</div>
                      <input className="inp" value={notif.slack_webhook}
                        onChange={e=>setNotif(n=>({...n, slack_webhook: e.target.value}))}/>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {section==='api-keys' && (
            <div className="card">
              <div className="card-hd"><h3>api keys</h3></div>
              <div className="card-bd stack stack-3">
                {[
                  {name:'andrea-production', key:'sk_finna_prod_••••••••••••••••3f8a', created:'Jan 10, 2026', last:'2 hours ago', scopes:['read','write']},
                  {name:'ci-pipeline',       key:'sk_finna_ci_••••••••••••••••9c2d', created:'Feb 20, 2026', last:'1 day ago',    scopes:['read']},
                ].map(api => (
                  <div key={api.name} style={{ border: '1px solid var(--border)', padding: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span className="mono" style={{ fontSize: 11 }}>{api.name}</span>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <Button size="sm" bracket>regenerate</Button>
                        <Button size="sm" bracket>revoke</Button>
                      </div>
                    </div>
                    <div className="mono muted" style={{ fontSize: 10, marginBottom: 8 }}>{api.key}</div>
                    <div style={{ display: 'flex', gap: 16, fontSize: 10 }} className="mono muted">
                      <span>created {api.created}</span>
                      <span>last used {api.last}</span>
                      <span>scopes · {api.scopes.join(', ')}</span>
                    </div>
                  </div>
                ))}
                <Button size="sm" bracket>+ new api key</Button>
              </div>
            </div>
          )}

          {section==='appearance' && (
            <div className="card">
              <div className="card-hd"><h3>appearance</h3></div>
              <div className="card-bd stack stack-4">
                <div>
                  <div className="label">theme</div>
                  <select className="sel" defaultValue="dark">
                    <option value="dark">dark</option>
                    <option value="light">light</option>
                    <option value="system">system</option>
                  </select>
                </div>
                <div>
                  <div className="label">date range picker</div>
                  <select className="sel" defaultValue="mtd">
                    <option value="mtd">mtd · month to date</option>
                    <option value="7d">last 7d</option>
                    <option value="30d">last 30d</option>
                    <option value="90d">last 90d</option>
                    <option value="custom">custom range</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {section==='data' && (
            <div className="card">
              <div className="card-hd"><h3>data & retention</h3></div>
              <div className="card-bd stack stack-3">
                <div style={{ border: '1px solid var(--border)', padding: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>Raw cost records</div>
                  <div className="mono muted" style={{ fontSize: 11, marginBottom: 10 }}>retention · 90 days · 2.4M records · ~18 GB</div>
                  <Button size="sm" bracket>export csv</Button>
                </div>
                <div style={{ border: '1px solid var(--border)', padding: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>Enriched records</div>
                  <div className="mono muted" style={{ fontSize: 11, marginBottom: 10 }}>retention · 365 days · 890K records · ~7 GB</div>
                  <Button size="sm" bracket>export csv</Button>
                </div>
                <div style={{ border: '1px solid var(--danger)', padding: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--danger)' }}>Danger zone</div>
                  <div className="mono muted" style={{ fontSize: 11, marginBottom: 10 }}>permanent deletion cannot be undone</div>
                  <Button size="sm" variant="danger" bracket onClick={()=>setDelDialog(true)}>delete all data</Button>
                </div>
              </div>
            </div>
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
