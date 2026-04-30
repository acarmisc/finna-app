import { useAuthStore } from '@/store/auth'

// Full API Client for Hooks
// Simplified version - uses Zustand auth store
export class APIClient {
  private token: string | null

  constructor() {
    const store = useAuthStore.getState()
    this.token = store.token || null
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<{ data?: T; error?: any; status: number }> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...Object.fromEntries(new Headers(options.headers).entries()),
    }
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    
    try {
      const resp = await fetch(`http://localhost:8000/api/v1${endpoint}`, { 
        ...options, 
        headers, 
        credentials: 'include' 
      })
      
      if (!resp.ok) {
        let parsed: any
        try { parsed = await resp.json() } catch { parsed = {} }
        return { 
          status: resp.status, 
          error: parsed.error || { message: 'API error' } 
        }
      }
      
      const data = await resp.json()
      return { data, status: resp.status }
    } catch (e: any) {
      return { 
        status: 0, 
        error: 
          { message: e.message || 'Network error' } 
      }
    }
  }

  // --- Authentication ---
  async login(username: string, password: string): Promise<{ data?: { token: string }; error?: any; status: number }> {
    const r1 = await this.request<{ token?: string; access_token?: string } | null>('/auth/login', { 
      method: 'POST', 
      body: JSON.stringify({ username, password }) 
    })
    let r = r1
    if (r1.error || !r1.data) {
      r = await this.request<{ token?: string; access_token?: string } | null>('/auth/token', { 
        method: 'POST', 
        body: JSON.stringify({ username, password }) 
      })
    }
    const token = r.data?.access_token || r.data?.token
    if (token) {
      this.token = token
      useAuthStore.getState().setToken(token)
    }
    return { 
      data: { token: (token as string) || '' }, 
      error: r.error || undefined,
      status: (r as any)?.status || 0
    }
  }

  // --- Configuration ---
  async getConnections(): Promise<{ data?: any[]; error?: any; status: number }> {
    return this.request('/config')
  }
  
  async getProjects(): Promise<{ data?: any[]; error?: any; status: number }> {
    return this.request('/config/projects')
  }

  // --- Costs ---
  async getCosts(params?: { provider?: string, project?: string, startDate?: string, endDate?: string }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/costs${qs ? '?' + qs : ''}`)
  }
  
  async getCostTotals(params?: { startDate?: string, endDate?: string }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/costs/totals${qs ? '?' + qs : ''}`)
  }
  
  async getDailyCosts(params?: { startDate?: string, endDate?: string, provider?: string }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/costs/daily${qs ? '?' + qs : ''}`)
  }
  
  async getCostsBySku(params?: { provider?: string, limit?: number }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/costs/by-sku${qs ? '?' + qs : ''}`)
  }

  // --- Alerts ---
  async getAlerts(params?: { status?: string, severity?: string, limit?: number }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/alerts${qs ? '?' + qs : ''}`)
  }
  
  async getAlertStats(): Promise<{ data?: any; error?: any; status: number }> {
    return this.request('/alerts/stats')
  }
  
  async acknowledgeAlert(id: string): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/alerts/${id}/acknowledge`, { method: 'POST', body: JSON.stringify({}) })
  }

  // --- Projects ---
  async getProject(slug: string): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/config/projects/${slug}`)
  }

  // --- Connections ---
  async getConnection(id: string): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/config/${id}`)
  }
  
  async testConnection(id: string): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/config/${id}/test`, { method: 'POST' })
  }
  
  async createConnection(data: any): Promise<{ data?: any; error?: any; status: number }> {
    return this.request('/config', { method: 'POST', body: JSON.stringify(data) })
  }
  
  async deleteConnection(id: string): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/config/${id}`, { method: 'DELETE' })
  }

  // --- Extractors ---
  async getExtractors(params?: { provider?: string, limit?: number }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/extractors${qs ? '?' + qs : ''}`)
  }
  
  async getExtractorRuns(params?: { configId?: string, limit?: number }): Promise<{ data?: any; error?: any; status: number }> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/extractors/runs${qs ? '?' + qs : ''}`)
  }
  
  async triggerExtractor(data: { config_id: string; extractor_type?: string }): Promise<{ data?: any; error?: any; status: number }> {
    return this.request('/extractors/run', { method: 'POST', body: JSON.stringify(data) })
  }

  // --- Dashboard ---
  async getDashboardStats(range?: string): Promise<{ data?: any; error?: any; status: number }> {
    const qs = range ? `?range=${range ?? ''}` : ''
    return this.request(`/dashboard/stats${qs}`)
  }
  
  async getTopProjects(range?: string, limit?: number): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/projects/top?range=${range || 'mtd'}&limit=${limit || 5}`)
  }
  
  async getRecentRuns(limit: number = 10): Promise<{ data?: any; error?: any; status: number }> {
    return this.request(`/extractors/runs?limit=${limit}`)
  }
}

export const getApiClient = () => new APIClient()