import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { money } from '@/components/shared/money'
import { useTheme } from '@/contexts/ThemeContext'
import { useToast } from '@/contexts/ToastContext'

interface ApiKey {
  id: string
  name: string
  key: string
  created: string
  last: string
  scopes: string[]
}

interface NotificationChannel {
  email_firing: boolean
  email_pending: boolean
  telegram_firing: boolean
  telegram_pending: boolean
  slack_firing: boolean
  slack_pending: boolean
  telegram_chat_id: string
  slack_webhook: string
}

interface UserPreferences {
  theme: 'dark' | 'light' | 'system'
  defaultWindow: string
  language: string
  timezone: string
}

const INITIAL_API_KEYS: ApiKey[] = [
  {id:'k1', name:'andrea-production', key:'sk_finna_prod_••••••••••••••••3f8a', created:'Jan 10, 2026', last:'2 hours ago', scopes:['read','write']},
  {id:'k2', name:'ci-pipeline',       key:'sk_finna_ci_••••••••••••••••9c2d', created:'Feb 20, 2026', last:'1 day ago',    scopes:['read']},
  {id:'k3', name:'billing-export',   key:'sk_finna_billing_••••••••••••1a2b', created:'Mar 5, 2026',  last:'3 days ago',  scopes:['read']},
]

const INITIAL_NOTIFS: NotificationChannel = {
  email_firing: true,
  email_pending: false,
  telegram_firing: true,
  telegram_pending: true,
  slack_firing: false,
  slack_pending: false,
  telegram_chat_id: '@acme_finops',
  slack_webhook: '',
}

const SECTIONS = [
  {id:'profile',      label: '// profile'},
  {id:'organization', label: '// organization'},
  {id:'api-keys',     label: '// api keys'},
  {id:'notifications',label: '// notifications'},
  {id:'preferences',  label: '// preferences'},
]

export function SettingsPage() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme()
  const { showToast, showSuccess, showError } = useToast()
  const [section, setSection] = useState('profile')
  const [saved, setSaved] = useState(false)
  const [delDialog, setDelDialog] = useState(false)
  const [isGeneratingKey, setIsGeneratingKey] = useState(false)
  const [generatedKey, setGeneratedKey] = useState<string | null>(null)

  const [profile, setProfile] = useState({
    name: 'Andrea Carmisciano',
    email: 'andrea@acme.co',
    timezone: 'Europe/Rome',
    locale: 'en-GB',
    currency: 'USD',
  })

  const [org, setOrg] = useState({
    name: 'Acme Corporation',
    billing_email: 'billing@acme.co',
    plan: 'enterprise',
    seats: 12,
    used_seats: 5,
  })

  const [notifs, setNotifs] = useState<NotificationChannel>(INITIAL_NOTIFS)

  const [keys, setKeys] = useState<ApiKey[]>(INITIAL_API_KEYS)
  const [preferences, setPreferences] = useState<UserPreferences>({
    theme: theme,
    defaultWindow: 'mtd',
    language: 'en',
    timezone: 'Europe/Rome',
  })

  useEffect(() => {
    if (section === 'preferences') {
      setPreferences(prev => ({ ...prev, theme }))
    }
  }, [theme, section])

  const save = () => {
    setSaved(true)
    showSuccess('Changes saved successfully')
    setTimeout(() => setSaved(false), 2000)
  }

  const deleteKey = (id: string) => {
    setKeys(prev => prev.filter(k => k.id !== id))
    showSuccess('API key revoked')
  }

  const generateKey = () => {
    setIsGeneratingKey(true)
    setTimeout(() => {
      const newKey: ApiKey = {
        id: `k${Date.now().toString().slice(-4)}`,
        name: 'new-api-key',
        key: `sk_finna_new_••••••••••••••••${Math.random().toString(36).substring(2, 10)}`,
        created: 'Just now',
        last: 'Never',
        scopes: ['read', 'write'],
      }
      setKeys(prev => [...prev, newKey])
      setGeneratedKey(newKey.key)
      setIsGeneratingKey(false)
      showToast('API key created', 'success', {
        action: {
          label: 'Copy',
          onClick: () => {
            navigator.clipboard.writeText(newKey.key)
            showToast('Key copied to clipboard')
          },
        },
      })
    }, 1000)
  }

  const toggleNotif = (key: keyof NotificationChannel) => {
    setNotifs(prev => ({ ...prev, [key]: !prev[key] }))
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
        <div className="space-y-0.5">
          {SECTIONS.map(s => (
            <button
              key={s.id}
              onClick={() => setSection(s.id)}
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

        <div>
          {section==='profile' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">profile</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 rounded bg-muted flex items-center justify-center font-mono text-2xl">
                    AC
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <div>avatar.png (2.4 MB)</div>
                    <Button size="sm" variant="outline" className="mt-2">upload new</Button>
                  </div>
                </div>
                {([
                  {k:'name',        label:'full name'},
                  {k:'email',       label:'email address'},
                  {k:'timezone',    label:'timezone'},
                  {k:'locale',      label:'locale'},
                  {k:'currency',    label:'default currency'},
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
              </CardContent>
            </Card>
          )}

          {section==='organization' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">organization</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-12">
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">organization name</div>
                    <div className="font-mono text-sm">{org.name}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">billing email</div>
                    <div className="font-mono text-sm">{org.billing_email}</div>
                  </div>
                </div>
                <div className="flex items-center gap-12">
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">plan tier</div>
                    <div className="font-mono text-sm">
                      <span className="inline-block px-2 py-0.5 rounded bg-muted text-muted-foreground">{org.plan}</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">seat usage</div>
                    <div className="font-mono text-sm">{org.used_seats}/{org.seats} seats</div>
                  </div>
                </div>
                <div className="border border-border p-4 mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-sm text-foreground">Upgrade to Enterprise</span>
                    <Button size="sm" variant="outline">upgrade</Button>
                  </div>
                  <div className="text-xs font-mono text-muted-foreground">Get advanced features: SSO, audit logs, and priority support</div>
                </div>
              </CardContent>
            </Card>
          )}

          {section==='api-keys' && (
            <Card>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">api keys</CardTitle>
                  <Button size="sm" variant="default" onClick={generateKey} disabled={isGeneratingKey}>
                    {isGeneratingKey ? '[ generating ]' : '+ new api key'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {generatedKey && (
                  <div className="border border-accent bg-accent/10 p-3 mb-3 font-mono text-xs text-accent">
                    ✅ Copy this key now — it will not be shown again!
                  </div>
                )}
                {keys.map(api => (
                  <div key={api.id} className="border border-border p-4 relative group">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-foreground">{api.name}</span>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(api.key)
                            showToast('Key copied to clipboard')
                          }}
                        >
                          copy
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-danger hover:text-danger"
                          onClick={() => deleteKey(api.id)}
                        >
                          revoke
                        </Button>
                      </div>
                    </div>
                    <div className="font-mono text-[10px] text-muted-foreground break-all mb-2">{api.key}</div>
                    <div className="flex gap-4 text-[10px] font-mono text-muted-foreground">
                      <span>created {api.created}</span>
                      <span>last used {api.last}</span>
                      <span>scopes · {api.scopes.join(', ')}</span>
                    </div>
                  </div>
                ))}
                {keys.length === 0 && (
                  <div className="text-center py-8 border border-border border-dashed rounded text-muted-foreground">
                    No API keys created yet
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {section==='notifications' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">notification channels</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">email</div>
                  <div className="space-y-2">
                    {(['firing', 'pending'] as const).map(status => (
                      <div key={status} className="flex items-center justify-between">
                        <label className="text-sm text-foreground">
                          email · {status} alerts
                        </label>
                        <button
                          onClick={() => toggleNotif(`email_${status}` as keyof NotificationChannel)}
                          className="w-9 h-5 border border-border relative transition-colors"
                          style={{
                            background: notifs[`email_${status}`] ? 'var(--accent)' : 'var(--surface-2)',
                          }}
                        >
                          <span className="absolute top-0.5 transition-all"
                            style={{
                              left: notifs[`email_${status}`] ? '18px' : '0px',
                              color: 'var(--bg)'
                            }}>
                            ●
                          </span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-border pt-4 space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">telegram</div>
                  <div className="space-y-2">
                    {(['firing', 'pending'] as const).map(status => (
                      <div key={status} className="flex items-center justify-between">
                        <label className="text-sm text-foreground">
                          telegram · {status} alerts
                        </label>
                        <button
                          onClick={() => toggleNotif(`telegram_${status}` as keyof NotificationChannel)}
                          className="w-9 h-5 border border-border relative transition-colors"
                          style={{
                            background: notifs[`telegram_${status}`] ? 'var(--accent)' : 'var(--surface-2)',
                          }}
                        >
                          <span className="absolute top-0.5 transition-all"
                            style={{
                              left: notifs[`telegram_${status}`] ? '18px' : '0px',
                              color: 'var(--bg)'
                            }}>
                            ●
                          </span>
                        </button>
                      </div>
                    ))}
                  </div>
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">telegram chat id</label>
                    <Input
                      className="font-mono text-xs max-w-sm"
                      value={notifs.telegram_chat_id}
                      onChange={e=>setNotifs(n=>({...n, telegram_chat_id: e.target.value}))}
                    />
                  </div>
                </div>

                <div className="border-t border-border pt-4 space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">slack</div>
                  <div className="space-y-2">
                    {(['firing', 'pending'] as const).map(status => (
                      <div key={status} className="flex items-center justify-between">
                        <label className="text-sm text-foreground">
                          slack · {status} alerts
                        </label>
                        <button
                          onClick={() => toggleNotif(`slack_${status}` as keyof NotificationChannel)}
                          className="w-9 h-5 border border-border relative transition-colors"
                          style={{
                            background: notifs[`slack_${status}`] ? 'var(--accent)' : 'var(--surface-2)',
                          }}
                        >
                          <span className="absolute top-0.5 transition-all"
                            style={{
                              left: notifs[`slack_${status}`] ? '18px' : '0px',
                              color: 'var(--bg)'
                            }}>
                            ●
                          </span>
                        </button>
                      </div>
                    ))}
                  </div>
                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-1.5">slack webhook url</label>
                    <Input
                      className="font-mono text-xs max-w-sm"
                      value={notifs.slack_webhook}
                      onChange={e=>setNotifs(n=>({...n, slack_webhook: e.target.value}))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {section==='preferences' && (
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-muted-foreground">preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">theme</label>
                  <Select defaultValue={theme} onValueChange={(v: any) => setTheme(v)}>
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dark">dark</SelectItem>
                      <SelectItem value="light">light</SelectItem>
                      <SelectItem value="system">system (auto)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">default date range</label>
                  <Select defaultValue={preferences.defaultWindow} onValueChange={(v: any) => setPreferences(p => ({...p, defaultWindow: v}))}>
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mtd">mtd · month to date</SelectItem>
                      <SelectItem value="7d">last 7d</SelectItem>
                      <SelectItem value="30d">last 30d</SelectItem>
                      <SelectItem value="90d">last 90d</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">language</label>
                  <Select defaultValue={preferences.language} onValueChange={(v: any) => setPreferences(p => ({...p, language: v}))}>
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English (US)</SelectItem>
                      <SelectItem value="en-GB">English (UK)</SelectItem>
                      <SelectItem value="de">Deutsch</SelectItem>
                      <SelectItem value="fr">Français</SelectItem>
                      <SelectItem value="it">Italiano</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground block mb-2">timezone</label>
                  <Select defaultValue={preferences.timezone} onValueChange={(v: any) => setPreferences(p => ({...p, timezone: v}))}>
                    <SelectTrigger className="font-mono text-xs max-w-xs"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="UTC">UTC</SelectItem>
                      <SelectItem value="Europe/Rome">Europe/Rome</SelectItem>
                      <SelectItem value="America/New_York">America/New_York</SelectItem>
                      <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="border border-border p-4 bg-background">
                  <div className="text-sm font-semibold text-foreground mb-2">appearance</div>
                  <div className="flex items-center justify-between">
                    <label className="text-sm text-foreground cursor-pointer">show scanlines overlay</label>
                    <button className="w-9 h-5 border border-border relative">
                      <span className="absolute top-0.5 left-18 transition-all" style={{ color: 'var(--bg)' }}>●</span>
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={delDialog}
        onClose={() => setDelDialog(false)}
        onConfirm={() => setDelDialog(false)}
        title="Delete all data · IRREVERSIBLE"
        message="This will permanently delete all cost records, alerts, and run history. This action cannot be undone."
        variant="danger"
      />
    </div>
  )
}

export default SettingsPage
