import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '@/components/shared'
import { cn } from '@/lib/utils'

export interface SidebarProps {
  collapsed?: boolean
  onToggle?: () => void
  activeBase?: string
  onLogout?: () => void
  alertCount?: number
  userEmail?: string
  userOrg?: string
  apiHealthy?: boolean
}

type NavItem = {
  id: string
  label: string
  icon: string
  path: string
  countKey?: string
}

type SectionItem = { sec: string }

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
  { id: 'settings', label: 'Settings', icon: 'settings-2', path: '/settings' },
]

interface NavLinkProps {
  item: NavItem
  active: boolean
  count?: number
  collapsed?: boolean
  onClick: (path: string) => void
}

const NavLink = React.memo<NavLinkProps>(({ item, active, count, collapsed, onClick }) => {
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    onClick(item.path)
  }, [item.path, onClick])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick(item.path)
    }
  }, [item.path, onClick])

  return (
    <a
      className={cn('sb-item', active && 'active')}
      title={collapsed ? item.label : undefined}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      href={`#${item.path}`}
      role="menuitem"
      tabIndex={0}
      aria-current={active ? 'page' : undefined}
    >
      <Icon name={item.icon} size={16} aria-hidden="true" />
      <span className="label">{item.label}</span>
      {item.countKey != null && count != null && count > 0 && (
        <span className="count" aria-label={`${count} items`}>{count}</span>
      )}
    </a>
  )
})
NavLink.displayName = 'NavLink'

interface MenuItemProps {
  icon: string
  label: string
  danger?: boolean
  onClick: () => void
}

const menuItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '8px 12px',
  fontSize: 12,
  cursor: 'pointer',
}

const MenuItem = React.memo<MenuItemProps>(({ icon, label, danger, onClick }) => {
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    onClick()
  }, [onClick])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }, [onClick])

  return (
    <a
      style={{
        ...menuItemStyle,
        color: danger ? 'var(--danger)' : 'var(--fg)',
        borderBottom: '1px solid var(--border-2)',
        fontFamily: danger ? 'JetBrains Mono, monospace' : undefined,
      }}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      href="#"
      role="menuitem"
      tabIndex={0}
    >
      <Icon name={icon} size={14} aria-hidden="true" />
      <span>{label}</span>
    </a>
  )
})
MenuItem.displayName = 'MenuItem'

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggle,
  activeBase = '/dashboard',
  onLogout,
  alertCount = 0,
  userEmail = 'finops@acme.co',
  userOrg = 'API',
  apiHealthy = true,
}) => {
  const [menu, setMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const navigate = useNavigate()

  const handleNavigate = useCallback((path: string) => {
    navigate(path)
  }, [navigate])

  const handleToggleMenu = useCallback(() => {
    setMenu((m: boolean) => !m)
  }, [])

  const handleLogout = useCallback(() => {
    setMenu(false)
    onLogout?.()
  }, [onLogout])

  const handleSettings = useCallback(() => {
    setMenu(false)
    navigate('/settings')
  }, [navigate])

  useEffect(() => {
    if (!menu) return
    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuRef.current && !menuRef.current.contains(e.target as Node) &&
        triggerRef.current && !triggerRef.current.contains(e.target as Node)
      ) {
        setMenu(false)
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenu(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [menu])

  const navSections = useMemo(() => {
    const sections: Array<{ sec?: string; items: NavItem[] }> = []
    let current: { sec?: string; items: NavItem[] } = { items: [] }
    for (const item of NAV_ITEMS) {
      if ('sec' in item) {
        if (current.items.length > 0) sections.push(current)
        current = { sec: item.sec, items: [] }
      } else {
        current.items.push(item as NavItem)
      }
    }
    if (current.items.length > 0) sections.push(current)
    return sections
  }, [])

  const counts: Record<string, number> = useMemo(() => ({ alerts: alertCount }), [alertCount])

  return (
    <aside className={cn('sb', collapsed && 'sb-collapsed')} aria-label="Main navigation">
      <div
        className="sb-logo"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onToggle?.() }}
      >
        <span className="caret" aria-hidden="true">{collapsed ? '‹' : '›'}</span>
        {!collapsed && (
          <>
            <span className="wordmark">finna</span>
            <span className="cursor" aria-hidden="true" />
          </>
        )}
      </div>
      <nav className="sb-nav" role="navigation" aria-label="Primary">
        {navSections.map((section, si) => (
          <React.Fragment key={section.sec ?? `section-${si}`}>
            {section.sec && (
              <div className="sb-section" aria-hidden="true">{section.sec}</div>
            )}
            {section.items.map((item) => (
              <NavLink
                key={item.id}
                item={item}
                active={activeBase === item.path}
                count={item.countKey ? counts[item.countKey] : undefined}
                collapsed={collapsed}
                onClick={handleNavigate}
              />
            ))}
          </React.Fragment>
        ))}
      </nav>
      <div className="sb-foot" style={{ position: 'relative' }}>
        <div className="avatar" aria-hidden="true">FN</div>
        <div className="who">
          <div className="name">{userEmail}</div>
          <div className="org">{userOrg} · {apiHealthy ? 'healthy' : 'degraded'}</div>
        </div>
        <span
          className="health"
          title={apiHealthy ? 'API healthy' : 'API degraded'}
          aria-label={apiHealthy ? 'API healthy' : 'API degraded'}
        />
        <button
          ref={triggerRef}
          className="icon-btn"
          onClick={handleToggleMenu}
          title="Account"
          aria-label="Account menu"
          aria-expanded={menu}
          aria-controls={menu ? 'sb-account-menu' : undefined}
          aria-haspopup="menu"
        >
          <Icon name="chevron-up" size={14} aria-hidden="true" />
        </button>
        {menu && (
          <div
            id="sb-account-menu"
            ref={menuRef}
            role="menu"
            aria-label="Account menu"
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
            <MenuItem icon="settings-2" label="Settings" onClick={handleSettings} />
            <MenuItem icon="log-out" label="Log out" danger onClick={handleLogout} />
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar