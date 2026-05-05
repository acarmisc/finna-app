// Config/Connection API client
import { apiRequest, buildQueryString } from './request'

export const configsClient = {
  async getConnections() {
    return apiRequest('/config')
  },

  async getConnection(id: string) {
    return apiRequest(`/config/${id}`)
  },

  async testConnection(id: string) {
    return apiRequest(`/config/${id}/test`, { method: 'POST' })
  },

  async createConnection(data: unknown) {
    return apiRequest('/config', { method: 'POST', body: JSON.stringify(data) })
  },

  async deleteConnection(id: string) {
    return apiRequest(`/config/${id}`, { method: 'DELETE' })
  },

  async getProjects() {
    return apiRequest('/config/projects')
  },

  async getProject(slug: string) {
    return apiRequest(`/config/projects/${slug}`)
  },

  async createProject(data: unknown) {
    return apiRequest('/config/projects', { method: 'POST', body: JSON.stringify(data) })
  },
}