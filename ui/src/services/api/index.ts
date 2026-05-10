// API clients - split by domain for better modularity
// Use specific clients: costsClient, alertsClient, configsClient
// Or use the legacy client via getApiClient() for backward compatibility
import { useAuthStore } from '@/store/auth'
import { apiRequest, buildQueryString } from './request'
import { costsClient } from './costs'
import { alertsClient } from './alerts'
import { configsClient } from './configs'

// Re-export specialized clients
export { costsClient } from './costs'
export { alertsClient } from './alerts'
export { configsClient } from './configs'

// Legacy unified client - wraps all specialized clients for backward compatibility
export class APIClient {
  // --- Authentication ---
  async login(username: string, password: string): Promise<{ data?: { token: string }; error?: any; status: number }> {
    const r1 = await apiRequest<{ token?: string; access_token?: string } | null>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    let r = r1
    if (r1.error || !r1.data) {
      r = await apiRequest<{ token?: string; access_token?: string } | null>('/auth/token', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
    }
    const token = r.data?.access_token || r.data?.token
    if (token) {
      useAuthStore.getState().setToken(token)
    }
    return {
      data: { token: (token as string) || '' },
      error: r.error || undefined,
      status: (r as any)?.status || 0,
    }
  }

  // Redirect specific methods to specialized clients
  async getCosts(params?: any) { return costsClient.getCosts(params) }
  async getCostTotals(params?: any) { return costsClient.getCostTotals(params) }
  async getDailyCosts(params?: any) { return costsClient.getDailyCosts(params) }
  async getCostsBySku(params?: any) { return costsClient.getCostsBySku(params) }

  async getAlerts(params?: any) { return alertsClient.getAlerts(params) }
  async getAlertStats() { return alertsClient.getAlertStats() }
  async acknowledgeAlert(id: string) { return alertsClient.acknowledgeAlert(id) }

  // --- Config/Connections ---
  async getConnections() { return configsClient.getConnections() }
  async getConnection(id: string) { return configsClient.getConnection(id) }
  async testConnection(id: string) { return configsClient.testConnection(id) }
  async createConnection(data: any) { return configsClient.createConnection(data) }
  async deleteConnection(id: string) { return configsClient.deleteConnection(id) }
  async getProjects(params?: { window?: string; start?: string; end?: string }) { return configsClient.getProjects(params) }
  async getProject(slug: string, params?: { window?: string; start?: string; end?: string }) { return configsClient.getProject(slug, params) }
  async createProject(data: any) { return configsClient.createProject(data) }

  // --- Extractors (inline for now) ---
  async getExtractors(params?: { provider?: string; limit?: number }) {
    return apiRequest(`/extractors${buildQueryString(params)}`)
  }
  async getExtractorRuns(params?: { configId?: string; limit?: number }) {
    return apiRequest(`/extractors/runs${buildQueryString(params)}`)
  }
  async triggerExtractor(data: { config_id: string; extractor_type?: string }) {
    return apiRequest('/extractors/run', { method: 'POST', body: JSON.stringify(data) })
  }
  async getExtractorLogs(runId: string) {
    return apiRequest(`/extractors/runs/${runId}/logs`)
  }

  // --- Dashboard (inline for now) ---
  async getDashboardStats(range?: string) {
    const qs = range ? `?range=${range}` : ''
    return apiRequest(`/dashboard/stats${qs}`)
  }
  async getTopProjects(range?: string, limit?: number) {
    return apiRequest(`/projects/top?range=${range || 'mtd'}&limit=${limit || 5}`)
  }
  async getRecentRuns(limit: number = 10) {
    return apiRequest(`/extractors/runs?limit=${limit}`)
  }
}

export const getApiClient = () => new APIClient()