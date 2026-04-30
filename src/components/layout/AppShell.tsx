import React, { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { useNavigate } from 'react-router-dom'

export interface AppShellProps {
  children: React.ReactNode | ((route: RouteState, ctx: { range: string; customRange: { start: string; end: string } | null }) => React.ReactNode)
  title?: string
  collapsed?: boolean
  onToggleSidebar?: () => void
  onLogout?: () => void
}

export interface RouteState {
  path: string
  base: string
  sub: string | null
  parts: string[]
  qs: URLSearchParams
}

function useHashRoute(): RouteState {
  const [route, setRoute] = useState<RouteState>(() => parseHash())

  React.useEffect(() => {
    const onChange = () => setRoute(parseHash())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return route
}

function parseHash(): RouteState {
  const raw = window.location.hash.replace(/^#/, '') || '/dashboard'
  const [path, query = ''] = raw.split('?')
  const parts = path.split('/').filter(Boolean)
  const base = '/' + (parts[0] || 'dashboard')
  const sub = parts[1] || null
  const qs = new URLSearchParams(query)
  return { path, base, sub, parts, qs }
}

const AppShell: React.FC<AppShellProps> = ({
  children,
  title = 'FinOps Console',
  collapsed: initialCollapsed = false,
  onToggleSidebar,
  onLogout,
}) => {
  const navigate = useNavigate()
  const route = useHashRoute()
  const [collapsed, setCollapsed] = useState(initialCollapsed)

  useEffect(() => {
  }, [])

  const handleToggle = onToggleSidebar || (() => { setCollapsed((v: boolean) => !v) })

  return (
    <div className={`app ${collapsed ? 'collapsed' : ''}`}>
      <Sidebar
        collapsed={collapsed}
        onToggle={handleToggle}
        activeBase={route.base}
        onLogout={onLogout}
      />
      <TopBar route={route} />
      <main className="main">
        {typeof children === 'function'
          ? children(route, {
              range: route.qs.get('window') || 'mtd',
              customRange: route.qs.get('start')
                ? {
                    start: route.qs.get('start')!,
                    end: route.qs.get('end')!,
                  }
                : null,
            })
          : children}
      </main>
      <div className="sidebar-toggle" onClick={handleToggle}>
        <span className="expand-icon">☰</span>
        <span className="collapse-icon">✕</span>
      </div>
    </div>
  )
}

export default AppShell
