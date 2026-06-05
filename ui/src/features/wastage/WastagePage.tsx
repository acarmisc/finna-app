import { useState } from 'react'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/shared/Button'
import { useToast } from '@/contexts/ToastContext'
import {
  useWastageFindings,
  useWastageSummary,
  useWastageRules,
  useAckFinding,
  useResolveFinding,
  useIgnoreFinding,
  useTriggerScan,
} from '@/api/hooks/useWastage'
import type { WastageFinding } from '@/types/wastage'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`
  const days = Math.floor(ms / 86_400_000)
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

function fmtUsd(n: number): string {
  return `€${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function truncate(s: string, max = 40): string {
  return s.length <= max ? s : '…' + s.slice(-max)
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'var(--danger)',
  high: '#f97316',
  medium: 'var(--warning)',
  low: 'var(--fg-muted)',
  info: 'var(--primary)',
}

// ---------------------------------------------------------------------------
// Detail Drawer
// ---------------------------------------------------------------------------

interface DrawerProps {
  finding: WastageFinding | null
  onClose: () => void
  onAck: (f: WastageFinding) => void
  onResolve: (f: WastageFinding) => void
  onIgnore: (f: WastageFinding, reason: string) => void
  isPending: boolean
}

function DetailDrawer({ finding, onClose, onAck, onResolve, onIgnore, isPending }: DrawerProps) {
  const [ignoreReason, setIgnoreReason] = useState('')
  const [showIgnore, setShowIgnore] = useState(false)

  if (!finding) return null

  return (
    <div
      role="dialog"
      aria-label="Finding detail"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 480,
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        zIndex: 100,
        overflowY: 'auto',
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--fg)' }}>Finding detail</h2>
        <Button size="sm" variant="ghost" onClick={onClose}>✕</Button>
      </div>

      <div className="card">
        <div className="card-hd"><h3>{finding.rule_id}</h3></div>
        <div className="card-bd" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="chip">{finding.provider}</span>
            <span className="chip" style={{ color: SEVERITY_COLORS[finding.severity] }}>{finding.severity}</span>
            <StatusBadge status={finding.status} />
          </div>
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
            <div><b>Resource:</b> {finding.resource_id}</div>
            <div><b>Type:</b> {finding.resource_type}</div>
            {finding.region && <div><b>Region:</b> {finding.region}</div>}
            {finding.resource_group && <div><b>RG:</b> {finding.resource_group}</div>}
            <div><b>Account:</b> {finding.account_id}</div>
            <div><b>First seen:</b> {fmtAge(finding.first_seen_at)}</div>
            <div><b>Est. savings:</b> <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{fmtUsd(finding.estimated_monthly_usd)}/mo</span></div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-hd"><h3>Evidence</h3></div>
        <div className="card-bd">
          <pre style={{ fontSize: 11, color: 'var(--fg-muted)', overflowX: 'auto', margin: 0 }}>
            {JSON.stringify(finding.evidence, null, 2)}
          </pre>
        </div>
      </div>

      {finding.status === 'open' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button size="sm" bracket disabled={isPending} onClick={() => onAck(finding)}>ack</Button>
            <Button size="sm" bracket disabled={isPending} onClick={() => onResolve(finding)}>resolve</Button>
            <Button size="sm" variant="ghost" bracket onClick={() => setShowIgnore(!showIgnore)}>ignore</Button>
          </div>
          {showIgnore && (
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="inp"
                placeholder="Reason (optional)"
                value={ignoreReason}
                onChange={e => setIgnoreReason(e.target.value)}
                style={{ flex: 1 }}
              />
              <Button
                size="sm"
                bracket
                disabled={isPending}
                onClick={() => { onIgnore(finding, ignoreReason); setShowIgnore(false); setIgnoreReason('') }}
              >confirm</Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function WastagePage() {
  const toast = useToast()

  // Filters
  const [provider, setProvider] = useState('')
  const [severity, setSeverity] = useState('')
  const [ruleFilter, setRuleFilter] = useState('')
  const [status, setStatus] = useState('open')
  const [offset, setOffset] = useState(0)
  const LIMIT = 50

  // Selected finding for drawer
  const [selected, setSelected] = useState<WastageFinding | null>(null)

  // Data
  const filterParams = {
    provider: provider || undefined,
    severity: severity || undefined,
    rule_id: ruleFilter || undefined,
    status: status || undefined,
    limit: LIMIT,
    offset,
  }
  const { data: findingsResp, isLoading } = useWastageFindings(filterParams)
  const { data: summaryResp } = useWastageSummary()
  const { data: rulesResp } = useWastageRules()

  // Mutations
  const ackMut = useAckFinding()
  const resolveMut = useResolveFinding()
  const ignoreMut = useIgnoreFinding()
  const scanMut = useTriggerScan()

  const findings = findingsResp?.data ?? []
  const total = findingsResp?.total ?? 0
  const summary = summaryResp ?? { categories: [], total_monthly_usd: 0, total_finding_count: 0 }
  const rules = rulesResp?.rules ?? []

  const isPending = ackMut.isPending || resolveMut.isPending || ignoreMut.isPending

  const onAck = (f: WastageFinding) => {
    ackMut.mutate(f.finding_id, {
      onSuccess: () => { toast.showSuccess(`Acknowledged · ${f.rule_id}`); setSelected(null) },
      onError: () => toast.showError('Failed to acknowledge'),
    })
  }

  const onResolve = (f: WastageFinding) => {
    resolveMut.mutate(f.finding_id, {
      onSuccess: () => { toast.showSuccess(`Resolved · ${f.rule_id}`); setSelected(null) },
      onError: () => toast.showError('Failed to resolve'),
    })
  }

  const onIgnore = (f: WastageFinding, reason: string) => {
    ignoreMut.mutate({ findingId: f.finding_id, reason }, {
      onSuccess: () => { toast.showSuccess(`Ignored · ${f.rule_id}`); setSelected(null) },
      onError: () => toast.showError('Failed to ignore'),
    })
  }

  const onScan = () => {
    const p = provider || 'azure'
    scanMut.mutate(p, {
      onSuccess: () => toast.showSuccess(`Scan started · ${p}`),
      onError: () => toast.showError('Failed to start scan'),
    })
  }

  return (
    <div className="page">
      {/* ── Header ── */}
      <div className="page-head">
        <div>
          <h1>Resource Wastage</h1>
          <div className="sub">// {summary.total_finding_count} findings · €{summary.total_monthly_usd.toFixed(2)}/mo estimated savings</div>
        </div>
        <div className="actions">
          <Button icon="refresh-cw" variant="ghost" bracket disabled={scanMut.isPending} onClick={onScan}>
            {scanMut.isPending ? 'scanning…' : 'run scan'}
          </Button>
        </div>
      </div>

      {/* ── List-price disclaimer ── */}
      <div
        role="note"
        style={{
          background: 'rgba(250, 204, 21, 0.08)',
          border: '1px solid rgba(250, 204, 21, 0.25)',
          borderRadius: 4,
          padding: '8px 12px',
          fontSize: 12,
          color: 'var(--warning)',
          marginBottom: 12,
        }}
      >
        Estimates are based on public list prices. Verify actual savings in Cost Analysis before taking action.
      </div>

      {/* ── Summary cards ── */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div className="card" style={{ flex: '1 1 140px', padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Est. Savings</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent)' }}>{fmtUsd(summary.total_monthly_usd)}<span style={{ fontSize: 12, fontWeight: 400 }}>/mo</span></div>
        </div>
        <div className="card" style={{ flex: '1 1 140px', padding: '12px 16px' }}>
          <div style={{ fontSize: 11, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Findings</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--fg)' }}>{summary.total_finding_count}</div>
        </div>
        {summary.categories.slice(0, 4).map(cat => (
          <div key={cat.category} className="card" style={{ flex: '1 1 140px', padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{cat.category}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--fg)' }}>{cat.finding_count}</div>
            <div style={{ fontSize: 11, color: 'var(--accent)' }}>{fmtUsd(cat.total_monthly_usd)}/mo</div>
          </div>
        ))}
      </div>

      {/* ── Filter bar ── */}
      <div className="card mt-3">
        <div className="card-hd">
          <h3>Findings · {total}</h3>
          <div className="hstack" style={{ flexWrap: 'wrap', gap: 8 }}>
            <select className="sel" style={{ width: 'auto' }} value={provider} onChange={e => { setProvider(e.target.value); setOffset(0) }}>
              <option value="">provider: all</option>
              <option value="azure">azure</option>
              <option value="aws">aws</option>
              <option value="gcp">gcp</option>
            </select>
            <select className="sel" style={{ width: 'auto' }} value={severity} onChange={e => { setSeverity(e.target.value); setOffset(0) }}>
              <option value="">severity: all</option>
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
              <option value="info">info</option>
            </select>
            <select className="sel" style={{ width: 'auto' }} value={ruleFilter} onChange={e => { setRuleFilter(e.target.value); setOffset(0) }}>
              <option value="">rule: all</option>
              {rules.map(r => (
                <option key={r.id} value={r.id}>{r.id}</option>
              ))}
            </select>
            <select className="sel" style={{ width: 'auto' }} value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }}>
              <option value="">status: all</option>
              <option value="open">open</option>
              <option value="acked">acked</option>
              <option value="resolved">resolved</option>
              <option value="ignored">ignored</option>
            </select>
          </div>
        </div>

        {/* ── Table ── */}
        <div className="card-bd p0">
          <table className="tbl">
            <thead>
              <tr>
                <th>Resource</th>
                <th>Type</th>
                <th>Rule</th>
                <th>Severity</th>
                <th>Est. €/mo</th>
                <th>Region</th>
                <th>Age</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={9} className="muted" style={{ textAlign: 'center', padding: 24 }}>// loading…</td>
                </tr>
              )}
              {!isLoading && findings.length === 0 && (
                <tr>
                  <td colSpan={9} className="muted" style={{ textAlign: 'center', padding: 24 }}>// no findings match filters</td>
                </tr>
              )}
              {findings.map(f => (
                <tr
                  key={f.finding_id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(f)}
                >
                  <td className="mono" style={{ fontSize: 11, maxWidth: 200 }} title={f.resource_id}>
                    {truncate(f.resource_id)}
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{f.resource_type.split('/').pop()}</td>
                  <td><code style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{f.rule_id}</code></td>
                  <td>
                    <span style={{ fontSize: 11, fontWeight: 700, color: SEVERITY_COLORS[f.severity] }}>
                      {f.severity}
                    </span>
                  </td>
                  <td style={{ fontWeight: 700, color: 'var(--accent)', fontSize: 13 }}>
                    {fmtUsd(f.estimated_monthly_usd)}
                  </td>
                  <td className="mono muted" style={{ fontSize: 11 }}>{f.region ?? '—'}</td>
                  <td className="mono muted" style={{ fontSize: 11 }}>{fmtAge(f.first_seen_at)}</td>
                  <td><StatusBadge status={f.status} /></td>
                  <td onClick={e => e.stopPropagation()}>
                    <div className="hstack">
                      {f.status === 'open' && (
                        <Button size="sm" bracket disabled={isPending} onClick={() => onAck(f)}>ack</Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ── */}
        {(findingsResp?.has_prev || findingsResp?.has_next) && (
          <div style={{ display: 'flex', gap: 8, padding: '8px 16px', alignItems: 'center', borderTop: '1px solid var(--border)' }}>
            <Button size="sm" variant="ghost" bracket disabled={!findingsResp?.has_prev} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← prev</Button>
            <span className="muted" style={{ fontSize: 11, flex: 1, textAlign: 'center' }}>
              {offset + 1}–{Math.min(offset + LIMIT, total)} of {total}
            </span>
            <Button size="sm" variant="ghost" bracket disabled={!findingsResp?.has_next} onClick={() => setOffset(offset + LIMIT)}>next →</Button>
          </div>
        )}
      </div>

      {/* ── Detail drawer ── */}
      {selected && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 99 }}
            onClick={() => setSelected(null)}
          />
          <DetailDrawer
            finding={selected}
            onClose={() => setSelected(null)}
            onAck={onAck}
            onResolve={onResolve}
            onIgnore={onIgnore}
            isPending={isPending}
          />
        </>
      )}
    </div>
  )
}

export default WastagePage
