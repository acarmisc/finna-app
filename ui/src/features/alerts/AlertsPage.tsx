import { useState } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/shared/Button'
import { useAlerts, useAlertStats, useAcknowledgeAlert } from '@/api/hooks'
import { useToast } from '@/contexts/ToastContext'
import type { AlertRecord } from '@/types/api'

const statusOf = (a: AlertRecord) => a.is_acknowledged ? 'ack' : a.silenced_until ? 'silenced' : 'firing'

const fmtRel = (iso: string) => {
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60_000) return 'just now'
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`
  return `${Math.floor(ms / 86_400_000)}d ago`
}

export function AlertsPage() {
  const toast = useToast()
  const { data: alertsResp } = useAlerts({})
  const { data: statsResp } = useAlertStats()
  const ackMut = useAcknowledgeAlert()

  const [severity, setSeverity] = useState<string>('all')
  const [status, setStatus] = useState<string>('all')

  const alerts: AlertRecord[] = alertsResp?.alerts ?? []
  const stats = statsResp ?? { total: 0, firing: 0, pending: 0, acknowledged: 0, by_severity: {} as Record<string, number>, by_provider: {} as Record<string, number> }

  const filtered = alerts.filter(a => {
    const st = statusOf(a)
    if (severity !== 'all' && a.severity !== severity) return false
    if (status !== 'all' && st !== status) return false
    return true
  })

  const onAck = (a: AlertRecord) => {
    ackMut.mutate(a.id, {
      onSuccess: () => toast.showSuccess(`Acknowledged · ${a.title}`),
      onError: () => toast.showError('Failed to acknowledge'),
    })
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Alerts</h1>
          <div className="sub">// {stats.firing ?? 0} firing · {stats.acknowledged ?? 0} ack · {stats.total ?? 0} total · 30 days</div>
        </div>
        <div className="actions">
          <Button icon="plus" variant="primary" bracket>new rule</Button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd"><h3>Stats · 30 days</h3></div>
        <div className="card-bd">
          <div className="hstack-4" style={{ flexWrap: 'wrap', gap: 12 }}>
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>firing · <b style={{ color: 'var(--danger)' }}>{stats.firing ?? 0}</b></span>
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>ack · <b style={{ color: 'var(--warning)' }}>{stats.acknowledged ?? 0}</b></span>
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>total · <b style={{ color: 'var(--accent)' }}>{stats.total ?? 0}</b></span>
            <span style={{ width: 1, height: 16, background: 'var(--border)' }} />
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>critical · <b style={{ color: 'var(--danger)' }}>{stats.by_severity?.err ?? stats.by_severity?.critical ?? 0}</b></span>
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>warning · <b style={{ color: 'var(--warning)' }}>{stats.by_severity?.warn ?? stats.by_severity?.warning ?? 0}</b></span>
            <span className="chip" style={{ padding: '6px 12px', fontSize: 12 }}>info · <b style={{ color: 'var(--primary)' }}>{stats.by_severity?.ok ?? stats.by_severity?.info ?? 0}</b></span>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-hd">
          <h3>Active + recent</h3>
          <div className="hstack">
            <select className="sel" style={{ width: 'auto' }} value={status} onChange={e => setStatus(e.target.value)}>
              <option value="all">status: all</option>
              <option value="firing">firing</option>
              <option value="ack">acked</option>
              <option value="silenced">silenced</option>
            </select>
            <select className="sel" style={{ width: 'auto' }} value={severity} onChange={e => setSeverity(e.target.value)}>
              <option value="all">severity: all</option>
              <option value="err">critical</option>
              <option value="warn">warning</option>
              <option value="ok">info</option>
            </select>
          </div>
        </div>
        <div className="card-bd p0">
          <table className="tbl">
            <thead><tr>
              <th>Status</th><th>Severity</th><th>Description</th><th>Project</th><th>Rule</th><th>Triggered</th><th></th>
            </tr></thead>
            <tbody>
              {filtered.map(a => {
                const st = statusOf(a)
                return (
                  <tr key={a.id}>
                    <td><StatusBadge status={st} /></td>
                    <td><StatusBadge status={a.severity === 'err' ? 'critical' : a.severity === 'warn' ? 'warning' : 'info'} /></td>
                    <td style={{ maxWidth: 360 }}>{a.description ?? a.title}</td>
                    <td className="mono">
                      <Link to={`/projects/${a.resource}`}>{a.resource}</Link>
                    </td>
                    <td><code style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{a.service}</code></td>
                    <td className="mono muted" style={{ fontSize: 11 }}>{fmtRel(a.first_seen)}</td>
                    <td>
                      <div className="hstack">
                        {!a.is_acknowledged && <Button size="sm" bracket disabled={ackMut.isPending} onClick={() => onAck(a)}>ack</Button>}
                        <Button size="sm" variant="ghost" icon="more-horizontal">{''}</Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="muted" style={{ textAlign: 'center', padding: 24 }}>// no alerts match filters</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default AlertsPage
