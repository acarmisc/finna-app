import React, { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { OIDCProvidersSection } from './components/OIDCProvidersSection'

export function SettingsPage() {
  const [saved, setSaved] = useState(false)
  const [purgeDialog, setPurgeDialog] = useState(false)

  const save = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <div className="sub">// account, orchestrator, integrations</div>
        </div>
      </div>

      <div className="card">
        <div className="card-hd"><h3>Account</h3></div>
        <div className="card-bd stack stack-4">
          <div>
            <div className="label">email</div>
            <input className="inp" defaultValue="finops@acme.co" />
          </div>
          <div>
            <div className="label">org</div>
            <input className="inp" defaultValue="acme" disabled />
          </div>
          <div>
            <div className="label">default currency</div>
            <select className="sel" defaultValue="USD">
              <option>USD</option>
              <option>EUR</option>
              <option>GBP</option>
            </select>
          </div>
        </div>
        <div className="card-ft">
          <span className="mono muted" style={{ fontSize: 11 }}>// changes apply on save</span>
          <Button variant="primary" bracket onClick={save}>{saved ? '✓ saved' : 'save'}</Button>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd"><h3>Orchestrator</h3></div>
        <div className="card-bd stack stack-3">
          <div className="spread">
            <div>
              <div className="mono" style={{ fontSize: 12 }}>api endpoint</div>
              <div className="mono muted" style={{ fontSize: 11 }}>http://api.finna.dev</div>
            </div>
            <span className="badge ghost-accent"><span className="dot" />healthy · 42ms</span>
          </div>
          <div className="hr" />
          <div className="spread">
            <div>
              <div className="mono" style={{ fontSize: 12 }}>scheduler</div>
              <div className="mono muted" style={{ fontSize: 11 }}>nightly · 02:00 UTC</div>
            </div>
            <Button size="sm" bracket>edit schedule</Button>
          </div>
        </div>
      </div>

      <OIDCProvidersSection />

      <div className="card mt-3">
        <div className="card-hd"><h3>Danger zone</h3></div>
        <div className="card-bd">
          <div className="spread">
            <div>
              <div style={{ color: 'var(--fg)', fontWeight: 500 }}>Purge cost records</div>
              <div className="mono muted" style={{ fontSize: 11, marginTop: 4 }}>// delete all cost_records older than retention window</div>
            </div>
            <Button variant="danger" bracket icon="trash-2" onClick={() => setPurgeDialog(true)}>purge</Button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={purgeDialog}
        onClose={() => setPurgeDialog(false)}
        onConfirm={() => setPurgeDialog(false)}
        title="Purge cost records"
        message="This will permanently delete all cost records older than the retention window. This action cannot be undone."
        variant="danger"
      />
    </div>
  )
}

export default SettingsPage
