// Alerts API client
import { apiRequest, buildQueryString } from './request'

export const alertsClient = {
  async getAlerts(params?: Record<string, unknown>) {
    return apiRequest(`/alerts${buildQueryString(params)}`)
  },

  async getAlertStats() {
    return apiRequest('/alerts/stats')
  },

  async acknowledgeAlert(id: string) {
    return apiRequest(`/alerts/${id}/acknowledge`, { method: 'POST', body: JSON.stringify({}) })
  },
}