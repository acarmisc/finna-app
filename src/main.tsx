import { useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { DateRangeProvider } from '@/contexts/DateRangeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { queryClient } from '@/query/queryClient'
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
  ExtractorsPage,
  RunHistoryPage,
  DataSourcesPage,
} from '@/pages'

function Router() {
  const { logout } = useAuthStore()
  
  return (
    <AppShell title={CONFIG.APP_NAME} onLogout={() => { logout(); window.location.hash = '/login' }}>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsListPage />} />
        <Route path="/projects/:slug" element={<ProjectDetailPage />} />
        <Route path="/costs" element={<CostsPage />} />
        <Route path="/configs" element={<ConfigsListPage />} />
        <Route path="/configs/new" element={<ConfigCreatePage />} />
        <Route path="/configs/:id" element={<ConfigCreatePage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/extractors" element={<ExtractorsPage />} />
        <Route path="/runs" element={<RunHistoryPage />} />
        <Route path="/sources" element={<DataSourcesPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppShell>
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
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <DateRangeProvider>
            <ToastProvider>
              <AuthenticatedApp />
            </ToastProvider>
          </DateRangeProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

const rootEl = document.getElementById('root')
if (rootEl) createRoot(rootEl).render(<Root />)
