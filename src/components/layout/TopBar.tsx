import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/shared'

interface Notification {
  id: string
  title: string
  message: string
  time: string
  read: boolean
  type: 'alert' | 'info' | 'warning'
}

export interface TopBarProps {
  route?: {
    base: string
    sub: string | null
  }
}

interface DateRangePickerProps {
  range: string
  setRange: (range: string) => void
  customRange: { start: string; end: string } | null
  setCustomRange: (range: { start: string; end: string } | null) => void
  label: string
}

function DateRangePicker({ range, setRange, customRange, setCustomRange, label }: DateRangePickerProps) {
  const [open, setOpen] = useState(false)
  const [viewMonth, setViewMonth] = useState(() => {
    const d = customRange?.start ? new Date(customRange.start) : new Date(2026, 3, 1)
    return new Date(d.getFullYear(), d.getMonth(), 1)
  })
  const [draftStart, setDraftStart] = useState(customRange?.start || null)
  const [draftEnd, setDraftEnd] = useState(customRange?.end || null)

  const fmt = (iso: string) => {
    if (!iso) return '—'
    const [y, m, d] = iso.split('-').map(Number)
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return `${months[m - 1]} ${d}, ${y}`
  }

  const toIso = (y: number, m: number, d: number) =>
    `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`

  const presets = [
    ['mtd', 'Month to date'],
    ['7d', 'Last 7 days'],
    ['30d', 'Last 30 days'],
    ['90d', 'Last 90 days'],
  ]

  const pickPreset = (k: string) => {
    setRange(k)
    setCustomRange(null)
    setDraftStart(null)
    setDraftEnd(null)
    setOpen(false)
  }

  const onDayClick = (iso: string) => {
    if (!draftStart || (draftStart && draftEnd)) {
      setDraftStart(iso)
      setDraftEnd(null)
    } else {
      if (iso < draftStart) {
        setDraftEnd(draftStart)
        setDraftStart(iso)
      } else {
        setDraftEnd(iso)
      }
    }
  }

  const applyCustom = () => {
    if (draftStart && draftEnd) {
      setCustomRange({ start: draftStart, end: draftEnd })
      setRange('custom')
      setOpen(false)
    }
  }

  const daysInMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0).getDate()
  const firstDay = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1).getDay()
  const shiftMonth = (n: number) =>
    setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + n, 1))
  const monthLabel = viewMonth.toLocaleString('en-US', { month: 'long', year: 'numeric' })

  const cells: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)

  const inRange = (iso: string) => draftStart && draftEnd && iso >= draftStart && iso <= draftEnd
  const isEdge = (iso: string) => iso === draftStart || iso === draftEnd

  return (
    <div style={{ position: 'relative' }}>
      <button className="tb-daterange" onClick={() => setOpen((o) => !o)} title="Date range">
        <Icon name="calendar" size={12} />
        <span>{label}</span>
        <Icon name="chevron-down" size={12} />
      </button>
      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            background: 'var(--surface)',
            border: '1px solid var(--border-strong)',
            boxShadow: '0 6px 0 rgba(0,0,0,0.35)',
            zIndex: 100,
            display: 'flex',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              borderRight: '1px solid var(--border)',
              minWidth: 150,
              background: 'var(--surface-2)',
            }}
          >
            {presets.map(([k, l]) => (
              <button
                key={k}
                onClick={() => pickPreset(k)}
                style={{
                  padding: '9px 14px',
                  textAlign: 'left',
                  background: range === k ? 'var(--primary)' : 'transparent',
                  color: range === k ? 'var(--primary-fg)' : 'var(--fg)',
                  border: 'none',
                  borderBottom: '1px solid var(--border-2)',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono, monospace',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                {l}
              </button>
            ))}
            <div
              style={{
                padding: '9px 14px',
                fontSize: 10,
                color: 'var(--fg-subtle)',
                fontFamily: 'JetBrains Mono, monospace',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                borderTop: '1px solid var(--border)',
              }}
            >
              // custom →
            </div>
          </div>
          <div style={{ padding: 12, minWidth: 260 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 8,
              }}
            >
              <button
                onClick={() => shiftMonth(-1)}
                style={{
                  width: 22,
                  height: 22,
                  border: '1px solid var(--border)',
                  background: 'var(--surface-2)',
                  color: 'var(--fg-muted)',
                  cursor: 'pointer',
                }}
              >
                ‹
              </button>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11,
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--fg)',
                }}
              >
                {monthLabel}
              </div>
              <button
                onClick={() => shiftMonth(1)}
                style={{
                  width: 22,
                  height: 22,
                  border: '1px solid var(--border)',
                  background: 'var(--surface-2)',
                  color: 'var(--fg-muted)',
                  cursor: 'pointer',
                }}
              >
                ›
              </button>
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: 2,
                marginBottom: 4,
              }}
            >
              {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
                <div
                  key={i}
                  style={{
                    textAlign: 'center',
                    fontSize: 9,
                    color: 'var(--fg-subtle)',
                    fontFamily: 'JetBrains Mono, monospace',
                    padding: '2px 0',
                  }}
                >
                  {d}
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
              {cells.map((d, i) => {
                if (d === null) return <div key={i} style={{ height: 26 }} />
                const iso = toIso(viewMonth.getFullYear(), viewMonth.getMonth(), d)
                const edge = isEdge(iso)
                const mid = inRange(iso) && !edge
                return (
                  <button
                    key={i}
                    onClick={() => onDayClick(iso)}
                    style={{
                      height: 26,
                      border: '1px solid ' + (edge ? 'var(--primary)' : 'transparent'),
                      background: edge ? 'var(--primary)' : mid ? 'var(--surface-3)' : 'transparent',
                      color: edge ? 'var(--primary-fg)' : 'var(--fg)',
                      cursor: 'pointer',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                    }}
                  >
                    {d}
                  </button>
                )
              })}
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: 10,
                paddingTop: 10,
                borderTop: '1px solid var(--border)',
                gap: 8,
              }}
            >
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  color: 'var(--fg-muted)',
                }}
              >
                {fmt(draftStart!)} — {fmt(draftEnd!)}
              </div>
              <button
                onClick={applyCustom}
                disabled={!draftStart || !draftEnd}
                style={{
                  padding: '5px 10px',
                  background: draftStart && draftEnd ? 'var(--primary)' : 'var(--surface-2)',
                  color: draftStart && draftEnd ? 'var(--primary-fg)' : 'var(--fg-subtle)',
                  border:
                    '1px solid ' + (draftStart && draftEnd ? 'var(--primary)' : 'var(--border)'),
                  cursor: draftStart && draftEnd ? 'pointer' : 'not-allowed',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}
              >
                [ apply ]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const TopBar: React.FC<TopBarProps> = ({ route }) => {
  const navigate = useNavigate()
  const [range, setRange] = useState('mtd')
  const [customRange, setCustomRange] = useState<{ start: string; end: string } | null>(null)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const notificationsRef = useRef<HTMLDivElement>(null)
  const bellRef = useRef<HTMLButtonElement>(null)

  const mockNotifications: Notification[] = [
    { id: 'n1', title: 'Cost Alert', message: 'Azure cost spike detected in prod', time: '2m ago', read: false, type: 'warning' },
    { id: 'n2', title: 'Run Completed', message: 'GCP billing extraction completed', time: '15m ago', read: false, type: 'info' },
    { id: 'n3', title: 'Alert Acknowledged', message: 'Critical alert ack by user', time: '1h ago', read: true, type: 'alert' },
  ]
  const unreadCount = mockNotifications.filter(n => !n.read).length

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node) &&
          bellRef.current && !bellRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
    }
    if (notificationsOpen) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [notificationsOpen])

  const labelFor: Record<string, string> = {
    dashboard: 'Dashboard',
    projects: 'Projects',
    configs: 'Cloud configs',
    extractors: 'Extractors',
    costs: 'Cost explorer',
    alerts: 'Alerts',
    settings: 'Settings',
  }

  const key = route?.base?.replace('/', '') || 'dashboard'
  const crumbs = [{ label: 'finna', mono: true }, { label: labelFor[key] || key }]
  if (route?.sub) crumbs.push({ label: route.sub, mono: true })

  const ranges: [string, string][] = [
    ['mtd', 'MTD'],
    ['7d', '7d'],
    ['30d', '30d'],
    ['90d', '90d'],
  ]

  const presetLabel: Record<string, string> = {
    mtd: 'Apr 1 — Apr 24, 2026',
    '7d': 'Apr 18 — Apr 24',
    '30d': 'Mar 26 — Apr 24',
    '90d': 'Jan 24 — Apr 24',
  }

  const fmt = (iso: string) => {
    if (!iso) return ''
    const [y, m, d] = iso.split('-').map(Number)
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return `${months[m - 1]} ${d}`
  }

  const customLabel = customRange ? `${fmt(customRange.start)} — ${fmt(customRange.end)}` : null
  const label = range === 'custom' && customLabel ? customLabel : presetLabel[range] || presetLabel['mtd']

  const handleNavigate = (path: string) => {
    navigate(path)
  }

  return (
    <header className="tb">
      <div className="tb-crumb">
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="sep">/</span>}
            <span className={`${i === crumbs.length - 1 ? 'last' : ''} ${c.mono ? 'mono' : ''}`}>
              {c.label}
            </span>
          </React.Fragment>
        ))}
      </div>
      <div className="tb-actions">
        <div
          style={{
            display: 'flex',
            border: '1px solid var(--border)',
            background: 'var(--surface-2)',
          }}
        >
          {ranges.map(([k, l]) => (
            <button
              key={k}
              onClick={() => {
                setRange(k)
                setCustomRange(null)
              }}
              style={{
                padding: '5px 9px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                background: range === k ? 'var(--primary)' : 'transparent',
                color: range === k ? 'var(--primary-fg)' : 'var(--fg-muted)',
                border: 'none',
                borderRight: '1px solid var(--border)',
                cursor: 'pointer',
              }}
            >
              {l}
            </button>
          ))}
        </div>
        <DateRangePicker
          range={range}
          setRange={setRange}
          customRange={range === 'custom' ? customRange : null}
          setCustomRange={(range: { start: string; end: string } | null) => {
            if (range) {
              setCustomRange(range)
            } else {
              setRange('mtd')
            }
          }}
          label={label}
        />
        <div className="sep-v" />
        <button
          className="icon-btn"
          onClick={() => {
            const root = document.documentElement
            const isDark = root.classList.contains('dark')
            if (isDark) {
              root.classList.remove('dark')
              root.classList.add('light')
              root.setAttribute('data-theme', 'light')
            } else {
              root.classList.remove('light')
              root.classList.add('dark')
              root.setAttribute('data-theme', 'dark')
            }
          }}
          title="Toggle theme"
        >
          <Icon name={document.documentElement.classList.contains('dark') ? 'sun' : 'moon'} size={14} />
        </button>
        <div className="sep-v" />
        <div ref={notificationsRef} className="relative">
          <button ref={bellRef} className="tb-bell" onClick={() => setNotificationsOpen(!notificationsOpen)} title="Notifications">
            <Icon name="bell" size={14} />
            {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
          </button>
          {notificationsOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                width: 320,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                boxShadow: 'var(--pxshadow-3)',
                zIndex: 100,
              }}
            >
              <div
                style={{
                  padding: '10px 14px',
                  borderBottom: '1px solid var(--border)',
                  fontFamily: 'Doto, monospace',
                  fontSize: 12,
                  fontWeight: 800,
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  color: 'var(--fg-muted)',
                }}
              >
                Notifications
              </div>
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {mockNotifications.length === 0 ? (
                  <div style={{ padding: 20, textAlign: 'center', color: 'var(--fg-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                    // no new notifications
                  </div>
                ) : (
                  mockNotifications.map(n => (
                    <div
                      key={n.id}
                      onClick={() => {
                        if (n.type === 'alert' || n.type === 'warning') {
                          navigate('/alerts')
                          setNotificationsOpen(false)
                        }
                      }}
                      style={{
                        padding: '10px 14px',
                        borderBottom: '1px solid var(--border-2)',
                        cursor: 'pointer',
                        opacity: n.read ? 0.7 : 1,
                        background: n.read ? 'transparent' : 'var(--surface-2)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <span
                          style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 10,
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            color: n.type === 'warning' ? 'var(--warning)' : n.type === 'alert' ? 'var(--danger)' : 'var(--primary)',
                          }}
                        >
                          {n.type}
                        </span>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: 'var(--fg-muted)' }}>{n.time}</span>
                      </div>
                      <div style={{ fontFamily: 'Inter, system-ui, sans-serif', fontSize: 12, marginBottom: 4, color: 'var(--fg)' }}>
                        {n.title}
                      </div>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: 'var(--fg-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {n.message}
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div
                style={{
                  padding: '8px 14px',
                  borderTop: '1px solid var(--border)',
                  textAlign: 'center',
                }}
              >
                <button
                  onClick={() => setNotificationsOpen(false)}
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--primary)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  [ dismiss ]
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="sep-v" />
      </div>
    </header>
  )
}

export default TopBar
