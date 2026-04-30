import { useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import LoginComponent from '@/components/auth/LoginComponent'
import { AppShell } from '@/components/layout'
import CONFIG from '@/config/env'
import './index.css'

import {
  DashboardPage,
  ProjectsListPage,
  ProjectDetailPage,
  CostsPage,
  ConfigsListPage,
  ConfigCreatePage,
  AlertsPage,
  SettingsPage,
  RunHistoryPage,
  DataSourcesPage,
} from '@/pages'

function HashRouter({ children }: { children: (hash: string) => React.ReactNode }) {
  const [hash] = useState(() => window.location.hash.replace(/^#/, '') || '/dashboard')
  
  useEffect(() => {
    const onChange = () => window.location.hash = `#${window.location.hash.replace(/^#/, '') || '/dashboard'}`
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return <>{children(hash)}</>
}

function Router() {
  const { logout } = useAuthStore()
  
  return (
    <HashRouter>
      {(hash) => {
        const path = hash.startsWith('/') ? hash : '/dashboard'
        
        return (
          <AppShell title={CONFIG.APP_NAME} onLogout={() => { logout(); window.location.hash = '/login' }}>
            <Routes>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsListPage />} />
              <Route path="/projects/:slug" element={<ProjectDetailPage />} />
              <Route path="/costs" element={<CostsPage />} />
              <Route path="/configs" element={<ConfigsListPage />} />
              <Route path="/configs/new" element={<ConfigCreatePage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/runs" element={<RunHistoryPage />} />
              <Route path="/sources" element={<DataSourcesPage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </AppShell>
        )
      }}
    </HashRouter>
  )
}

function AuthenticatedApp() {
  const { checkAuth } = useAuthStore()
  
  useEffect(() => { checkAuth() }, [])
  
  if (!useAuthStore.getState().isAuthenticated) return <LoginComponent onLoginSuccess={() => {}} />
  
  return <Router />
}

function Root() {
  const { checkAuth } = useAuthStore()
  
  useEffect(() => {
    checkAuth()
    if (!window.location.hash) window.location.hash = '#/dashboard'
  }, [])

  return (
    <BrowserRouter>
      <AuthenticatedApp />
    </BrowserRouter>
  )
}

const rootEl = document.getElementById('root')
if (rootEl) createRoot(rootEl).render(<Root />)
