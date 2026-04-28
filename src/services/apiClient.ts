interface APIError {
  error: string
  message?: string
  detail?: string
}

interface ApiResponse<T> {
  data?: T
  error?: APIError
  status: number
}

export class APIClient {
  private baseUrl: string
  private token: string | null

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || 'http://localhost:8000'
    this.token = typeof window !== 'undefined' ? localStorage.getItem('finna-auth-token') : null
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...Object.fromEntries(new Headers(options.headers).entries()),
    }
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    try {
      const resp = await fetch(this.baseUrl + endpoint, { ...options, headers, credentials: 'include' })
      if (!resp.ok) {
        let parsed: any = { error: 'api_error' }
        try { parsed = await resp.json() } catch {}
        return { status: resp.status, error: { error: parsed.error || 'api_error', message: parsed.message, detail: parsed.detail } }
      }
      const data = await resp.json()
      return { data, status: resp.status }
    } catch (e: any) {
      return { status: 0, error: { error: 'network_error', message: e.message || 'Unknown error' } }
    }
  }

  async login(username: string, password: string): Promise<ApiResponse<{ token: string; access_token?: string }>> {
    // Prefer /auth/login (CLI-compatible) but fall back to /auth/token
    let r = await this.request<{ token?: string; access_token?: string; token_type?: string }>('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })
    if (r.error) {
      r = await this.request<{ token?: string; access_token?: string; token_type?: string }>('/api/v1/auth/token', { method: 'POST', body: JSON.stringify({ username, password }) })
    }
    const token = r.data?.access_token || r.data?.token
    if (token) {
      this.token = token
      localStorage.setItem('finna-auth-token', token)
    }
    return { data: { token: token || '' }, status: r.status, error: r.error }
  }

  // --- Configuration ---
  async getConnections(): Promise<ApiResponse<any[]>> { return this.request('/api/v1/config') }
  async getProjects(): Promise<ApiResponse<any[]>> { return this.request('/api/v1/config/projects') }

  // --- Costs ---
  async getCosts(params?: { provider?: string, project?: string, startDate?: string, endDate?: string }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/costs${qs ? '?' + qs : ''}`)
  }
  async getCostTotals(params?: { startDate?: string, endDate?: string }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/costs/totals${qs ? '?' + qs : ''}`)
  }
  async getDailyCosts(params?: { startDate?: string, endDate?: string, provider?: string }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/costs/daily${qs ? '?' + qs : ''}`)
  }
  async getCostsBySku(params?: { provider?: string, limit?: number }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/costs/by-sku${qs ? '?' + qs : ''}`)
  }

  // --- Alerts ---
  async getAlerts(params?: { status?: string, severity?: string, limit?: number }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as any).toString()
    return this.request(`/api/v1/alerts${qs ? '?' + qs : ''}`)
  }
  async getAlertStats(): Promise<ApiResponse<any>> { return this.request('/api/v1/alerts/stats') }
  async getActiveAlerts(): Promise<ApiResponse<any>> { return this.request('/api/v1/alerts/active') }
  async acknowledgeAlert(id: string): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/alerts/${id}/acknowledge`, { method: 'POST', body: JSON.stringify({}) })
  }

  // --- Extractors ---
  async getExtractorStatus(limit: number = 50): Promise<ApiResponse<any>> { return this.request(`/api/v1/extractors/status?limit=${limit}`) }
  async getExtractors(params?: { provider?: string, limit?: number }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/extractors${qs ? '?' + qs : ''}`)
  }
  async runExtractor(type: string, provider: string, configId?: string): Promise<ApiResponse<any>> {
    return this.request('/api/v1/extractors/run', { method: 'POST', body: JSON.stringify({ extractor_type: type, provider, config_id: configId }) })
  }

  // --- Health ---
  async healthCheck(): Promise<ApiResponse<any>> { return this.request('/healthz') }

  // --- Projects ---
  async getProject(slug: string): Promise<ApiResponse<any>> { return this.request(`/api/v1/config/projects/${slug}`) }

  // --- Connections ---
  async getConnection(id: string): Promise<ApiResponse<any>> { return this.request(`/api/v1/config/${id}`) }
  async testConnection(id: string): Promise<ApiResponse<any>> { return this.request(`/api/v1/config/${id}/test`, { method: 'POST' }) }
  async createConnection(data: any): Promise<ApiResponse<any>> { return this.request('/api/v1/config', { method: 'POST', body: JSON.stringify(data) }) }
  async deleteConnection(id: string): Promise<ApiResponse<any>> { return this.request(`/api/v1/config/${id}`, { method: 'DELETE' }) }

  // --- Extractors ---
  async getExtractorRuns(params?: { configId?: string, limit?: number }): Promise<ApiResponse<any>> {
    const qs = new URLSearchParams(params as Record<string, string>).toString()
    return this.request(`/api/v1/extractors/runs${qs ? '?' + qs : ''}`)
  }
  async triggerExtractor(data: { config_id: string; extractor_type?: string }): Promise<ApiResponse<any>> {
    return this.request('/api/v1/extractors/run', { method: 'POST', body: JSON.stringify(data) })
  }

  // --- Dashboard ---
  async getDashboardStats(range?: string): Promise<ApiResponse<any>> {
    const qs = range ? `?range=${range}` : ''
    return this.request(`/api/v1/dashboard/stats${qs}`)
  }
  async getTopProjects(range?: string, limit?: number): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/projects/top?range=${range || 'mtd'}&limit=${limit || 5}`)
  }
  async getRecentRuns(limit: number = 10): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/extractors/runs?limit=${limit}`)
  }
  
  // --- Alerts ---
  async getAlertingRules(): Promise<ApiResponse<any>> { return this.request(`/api/v1/alerts/rules`) }
  async createAlertingRule(data: any): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/alerts/rules`, { method: 'POST', body: JSON.stringify(data) })
  }
  
  // --- Settings ---
  async getProfile(): Promise<ApiResponse<any>> { return this.request(`/api/v1/auth/profile`) }
  async updateProfile(data: any): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/auth/profile`, { method: 'PUT', body: JSON.stringify(data) })
  }
  async getApiKeys(): Promise<ApiResponse<any>> { return this.request(`/api/v1/auth/api-keys`) }
  async createApiKey(name: string, scopes: string[]): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/auth/api-keys`, { method: 'POST', body: JSON.stringify({ name, scopes }) })
  }
  async deleteApiKey(id: string): Promise<ApiResponse<any>> {
    return this.request(`/api/v1/auth/api-keys/${id}`, { method: 'DELETE' })
  }
}

let client: APIClient | null = null
export function getApiClient(): APIClient {
  if (!client) client = new APIClient()
  return client
}
export default getApiClient
