// Base request handler shared by all API clients
import { useAuthStore } from '@/store/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error?: unknown) => {
  failedQueue.forEach(({ reject }) => reject(error))
  failedQueue = []
}

export const apiRequest = async <T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data?: T; error?: any; status: number }> => {
  const doRequest = async (): Promise<{ data?: T; error?: any; status: number }> => {
    const token = useAuthStore.getState().token
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...Object.fromEntries(new Headers(options.headers).entries()),
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    let resp: Response
    try {
      resp = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
        credentials: 'include',
      })
    } catch (e: any) {
      return { status: 0, error: { message: e.message || 'Network error' } }
    }

    if (resp.ok) {
      const data = await resp.json()
      return { data, status: resp.status }
    }

    if (resp.status === 401) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then(() => apiRequest(endpoint, options))
          .catch((err) => Promise.reject(err)) as Promise<{ data?: T; error?: any; status: number }>
      }

      if (!useAuthStore.getState().isAuthenticated) {
        let parsed: any
        try { parsed = await resp.json() } catch { parsed = {} }
        return { status: 401, error: parsed.error || { message: 'Unauthorized' } }
      }

      isRefreshing = true

      try {
        const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        })

        if (refreshResp.ok) {
          const refreshData = await refreshResp.json()
          if (refreshData?.access_token) {
            useAuthStore.getState().setToken(refreshData.access_token)
            processQueue()
            return apiRequest(endpoint, options) as Promise<{ data?: T; error?: any; status: number }>
          }
        }

        useAuthStore.getState().logout()
        processQueue(new Error('Session expired'))
        return { status: 401, error: { message: 'Session expired' } }
      } catch (refreshError: any) {
        useAuthStore.getState().logout()
        processQueue(refreshError)
        return { status: 401, error: { message: refreshError.message || 'Session expired' } }
      } finally {
        isRefreshing = false
      }
    }

    let parsed: any
    try { parsed = await resp.json() } catch { parsed = {} }
    return {
      status: resp.status,
      error: parsed.error || { message: 'API error' },
    }
  }

  return doRequest()
}

export function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return ''
  const entries = Object.entries(params)
    .filter(([, v]) => v != null)
    .map(([k, v]) => [camelToSnake(k), String(v)] as [string, string])
  const qs = new URLSearchParams(entries).toString()
  return qs ? '?' + qs : ''
}

function camelToSnake(s: string): string {
  return s.replace(/[A-Z]/g, m => '_' + m.toLowerCase())
}