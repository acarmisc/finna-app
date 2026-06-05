import React, { useState, useCallback, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/shared'
import { cn } from '@/lib/utils'

export interface SidebarProps {
  collapsed?: boolean
  onToggle?: () => void
  activeBase?: string
  onLogout?: () => void
  counts?: Record<string, number>
}

// Reusable Logo component
const Logo: React.FC<{ collapsed: boolean; onToggle: () => void }> = ({ collapsed, onToggle }) => (
  <div className="sb-logo" onClick={onToggle} role="button" tabIndex={0} aria-label="Toggle navigation">
    <span className="caret">{collapsed ? '‹' : '›'}</span>
    {!collapsed && (
      <>
        <span className="wordmark">finna</span>
        <span className="cursor" aria-hidden="true" />
      </>
    )}
  </div>
)

// Reusable NavItem component
interface NavItemProps {
  item: NavItem
  active: boolean
  collapsed: boolean
  counts: Record<string, number>
  onNavigate: (path: string) => void
}

const NavItem: React.FC<NavItemProps> = ({ item, active, collapsed, counts, onNavigate }) => {
  const isCollapsed = !!collapsed
  const handleClick = useCallback((e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault()
    onNavigate(item.path)
  }, [item.path, onNavigate])

  return (
    <a
      key={item.id}
      className={cn('sb-item', active && 'active')}
      href={`#${item.path}`}
      onClick={handleClick}
      data-label={item.label}
      title={isCollapsed ? item.label : undefined}
      aria-current={active ? 'page' : undefined}
    >
      <Icon name={item.icon} size={16} aria-hidden="true" />
      <span className="label">{item.label}</span>
      {item.countKey && counts[item.countKey] > 0 && (
        <span className="count" aria-label={`${item.label} count: ${counts[item.countKey]}`}>
          {counts[item.countKey]}
        </span>
      )}
    </a>
  )
}

// Reusable UserMenu component
interface UserMenuProps {
  open: boolean
  onToggle: () => void
  onNavigateToSettings: () => void
  onLogout: () => void
}

const UserMenu: React.FC<UserMenuProps> = ({ open, onToggle, onNavigateToSettings, onLogout }) => {
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onToggle()
    }
  }, [onToggle])

  return (
    <>
      <button
        className="icon-btn"
        onClick={onToggle}
        title="Account"
        aria-haspopup="true"
        aria-expanded={open}
        onKeyDown={handleKeyDown}
      >
        <Icon name="chevron-up" size={14} aria-hidden="true" />
      </button>

      {open && (
        <div
          role="menu"
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
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              onToggle()
            }
          }}
        >
          <a
            href="#/settings"
            onClick={(e) => {
              e.preventDefault()
              onToggle()
              onNavigateToSettings()
            }}
            role="menuitem"
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
            <Icon name="settings-2" size={14} aria-hidden="true" />
            <span>Settings</span>
          </a>
          <button
            onClick={(e) => {
              e.preventDefault()
              onToggle()
              onLogout()
            }}
            role="menuitem"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              fontSize: 12,
              color: 'var(--danger)',
              cursor: 'pointer',
              fontFamily: 'JetBrains Mono, monospace',
              background: 'none',
              border: 'none',
              width: '100%',
              textAlign: 'left',
            }}
          >
            <Icon name="log-out" size={14} aria-hidden="true" />
            <span>Log out</span>
          </button>
        </div>
      )}
    </>
  )
}

type NavItem = {
  id: string
  label: string
  icon: string
  path: string
  countKey?: string
}

type SectionItem = { sec: string }

const isSectionItem = (item: SectionItem | NavItem): item is SectionItem => 'sec' in item
const isNavItem = (item: SectionItem | NavItem): item is NavItem => !('sec' in item)

const NAV_ITEMS: Array<SectionItem | NavItem> = [
  { sec: 'Overview' },
  { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard', path: '/dashboard' },
  { id: 'costs', label: 'Cost explorer', icon: 'chart-line', path: '/costs' },
  { sec: 'Resources' },
  { id: 'projects', label: 'Projects', icon: 'folders', path: '/projects' },
  { id: 'configs', label: 'Cloud configs', icon: 'plug', path: '/configs' },
  { id: 'extractors', label: 'Extractors', icon: 'database', path: '/extractors' },
  { sec: 'Monitoring' },
  { id: 'alerts', label: 'Alerts', icon: 'bell', path: '/alerts', countKey: 'alerts' },
  { id: 'wastage', label: 'Wastage', icon: 'trash-2', path: '/wastage', countKey: 'wastage' },
  { id: 'settings', label: 'Settings', icon: 'settings-2', path: '/settings' },
]

const Sidebar: React.FC<SidebarProps> = ({
  collapsed: isCollapsedProp,
  onToggle,
  activeBase = '/dashboard',
  onLogout,
  counts: incomingCounts = {},
}) => {
  const collapsed = isCollapsedProp ?? false
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // Memoize counts object to prevent unnecessary recalculations
  const counts = useMemo(() => ({
    alerts: incomingCounts.alerts ?? 0, // Default to 0 if not provided
    ...incomingCounts,
  }), [incomingCounts])

  // Use useCallback for event handlers to prevent unnecessary re-renders
  const handleNavigate = useCallback((path: string) => {
    navigate(path)
  }, [navigate])

  const handleNavigateToSettings = useCallback(() => {
    navigate('/settings')
  }, [navigate])

  const handleLogout = useCallback(() => {
    onLogout?.()
  }, [onLogout])

  // Handle keyboard events for logo button
  const handleLogoKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onToggle?.()
    }
  }, [onToggle])

  return (
    <aside className={cn('sb', collapsed && 'sb-collapsed')} aria-label="Main navigation">
<Logo collapsed={collapsed ?? false} onToggle={onToggle ?? (() => {})} />
      
      <nav className="sb-nav" aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => {
          if (isSectionItem(item)) {
            return (
              <div key={item.sec} className="sb-section" role="separator" aria-label={item.sec}>
                {item.sec}
              </div>
            )
          }
          
          const active = activeBase === item.path
          
          return (
            <NavItem
              key={item.id}
              item={item as NavItem}
              active={active}
              collapsed={!!collapsed}
              counts={counts}
              onNavigate={handleNavigate}
            />
          )
        })}
      </nav>
      
      <div className="sb-foot" style={{ position: 'relative' }}>
        <div className="avatar" aria-label="User avatar">FN</div>
        <div className="who">
          <div className="name">finops@acme.co</div>
          <div className="org">API · healthy</div>
        </div>
        <span className="health" title="API healthy" aria-label="API status: healthy" />
        
        <UserMenu
          open={menuOpen}
          onToggle={() => setMenuOpen((m) => !m)}
          onNavigateToSettings={handleNavigateToSettings}
          onLogout={handleLogout}
        />
      </div>
    </aside>
  )
}

export default Sidebar