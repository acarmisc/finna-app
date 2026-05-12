// Base request handler shared by all API clients
import { useAuthStore } from '@/store/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'


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
      useAuthStore.getState().logout()
      return { status: 401, error: { message: 'Session expired' } }
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