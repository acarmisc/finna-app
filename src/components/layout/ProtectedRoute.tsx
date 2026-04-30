import React, { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'

export interface ProtectedRouteProps {
  children: React.ReactNode
  requireAuth?: boolean
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requireAuth = true }) => {
  const location = useLocation()
  const { token, loading } = useAuthStore()

  useEffect(() => {
    if (!loading && !token && requireAuth) {
      const params = new URLSearchParams()
      params.set('from', location.pathname + location.search)
      window.location.hash = `/login?${params.toString()}`
    }
  }, [token, loading, requireAuth, location])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-muted-foreground font-mono text-sm">authenticating...</div>
      </div>
    )
  }

  if (requireAuth && !token) {
    return <Navigate to="/login" replace />
  }

  if (!requireAuth && token) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
