import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/shared'
import { cn } from '@/lib/utils'

export interface SidebarProps {
  collapsed?: boolean
  onToggle?: () => void
  activeBase?: string
  onLogout?: () => void
}

const NAV = [
  { sec: 'Overview' },
  { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard', path: '/dashboard' },
  { id: 'costs', label: 'Cost explorer', icon: 'chart-line', path: '/costs' },
  { sec: 'Resources' },
  { id: 'projects', label: 'Projects', icon: 'folders', path: '/projects' },
  { id: 'configs', label: 'Cloud configs', icon: 'plug', path: '/configs' },
  { id: 'extractors', label: 'Extractors', icon: 'database', path: '/extractors' },
  { sec: 'Monitoring' },
  { id: 'alerts', label: 'Alerts', icon: 'bell', path: '/alerts', countKey: 'alerts' },
  { id: 'settings', label: 'Settings', icon: 'settings-2', path: '/settings' },
]

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle, activeBase = '/dashboard', onLogout }) => {
  const [menu, setMenu] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const counts: Record<string, number> = { alerts: 3 }

  const handleNavigate = (path: string) => {
    navigate(path)
  }

  return (
    <aside className={cn('sb', collapsed && 'sb-collapsed')}>
      <div className="sb-logo" onClick={onToggle} title={collapsed ? 'Expand' : 'Collapse'}>
        <span className="caret">&gt;</span>
        <span className="wordmark">finna</span>
        <span className="cursor" />
      </div>
      <nav className="sb-nav">
        {NAV.map((item, i) => {
          if (item.sec) return <div key={i} className="sb-section">{item.sec}</div>
          const active = activeBase === item.path
          return (
            <a
              key={item.id}
              className={cn('sb-item', active && 'active')}
              onClick={(e) => {
                e.preventDefault()
                handleNavigate(item.path!)
              }}
              href={`#${item.path}`}
            >
              <Icon name={item.icon!} size={16} />
              <span className="label">{item.label}</span>
              {item.countKey && counts[item.countKey] > 0 && (
                <span className="count">{counts[item.countKey]}</span>
              )}
            </a>
          )
        })}
      </nav>
      <div className="sb-foot" style={{ position: 'relative' }}>
        <div className="avatar">FN</div>
        <div className="who">
          <div className="name">finops@acme.co</div>
          <div className="org">API · healthy</div>
        </div>
        <span className="health" title="API healthy" />
        <button className="icon-btn" onClick={() => setMenu((m) => !m)} title="Account">
          <Icon name="chevron-up" size={14} />
        </button>
        {menu && (
          <div
            style={{
              position: 'absolute',
              bottom: 'calc(100% + 4px)',
              right: 8,
              left: 8,
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              boxShadow: '0 4px 0 rgba(0,0,0,0.3)',
              zIndex: 20,
            }}
          >
            <a
              href="#/settings"
              onClick={(e) => {
                e.preventDefault()
                setMenu(false)
                navigate('/settings')
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                fontSize: 12,
                color: 'var(--fg)',
                borderBottom: '1px solid var(--border-2)',
                cursor: 'pointer',
              }}
            >
              <Icon name="settings-2" size={14} />
              <span>Settings</span>
            </a>
            <a
              onClick={() => {
                setMenu(false)
                onLogout?.()
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                fontSize: 12,
                color: 'var(--danger)',
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              <Icon name="log-out" size={14} />
              <span>Log out</span>
            </a>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
