import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/store/auth'
import { getApiClient } from '@/services/apiClient'

/**
 * Creates a stable dependency key from params object.
 * Handles undefined values and ensures consistent ordering across runtimes.
 * Returns a string that uniquely represents the logical state of params.
 */
function createParamsKey<T extends Record<string, any>>(params?: T) {
  if (!params) return 'null'
  // Convert to sorted entries, filtering out undefined values for consistency
  const entries = Object.entries(params)
    .filter(([_, v]) => v !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify(entries)
}

export function useAuth() {
  const { checkAuth, isAuthenticated, logout } = useAuthStore()
  
  useEffect(() => { checkAuth() }, [])
  
  return { 
    authenticated: isAuthenticated,
    loading: !isAuthenticated,
    logout
  }
}

export function useCostTotals(params?: { startDate?: string, endDate?: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getCostTotals(params)
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load totals')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [createParamsKey(params)])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}

export function useDailyCosts(params?: { startDate?: string, endDate?: string, provider?: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getDailyCosts(params)
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load daily costs')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [createParamsKey(params)])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}

export function useCosts(params?: { provider?: string; project?: string; startDate?: string; endDate?: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getCosts(params)
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load costs')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [createParamsKey(params)])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}

export function useAlerts(params?: { status?: string; severity?: string; limit?: number }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setRefreshing(true)
    setError('')
    getApiClient().getAlerts(params)
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load alerts')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => { setLoading(false); setRefreshing(false) })
  }, [createParamsKey(params)])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, refreshing, error, refresh }
}

export function useAlertStats() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getAlertStats()
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load alert stats')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}

export function useConnections() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getConnections()
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load connections')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}

export function useProjects() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    getApiClient().getProjects()
      .then((r: any) => { 
        if (r.error) {
          setError(r.error.message || 'Failed to load projects')
        } else {
          setData(r.data)
        }
      })
      .catch((e: Error) => setError(e.message || 'Network error'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, refresh }
}
