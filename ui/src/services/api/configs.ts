// Config/Connection API client
import { apiRequest, buildQueryString } from './request'

interface ProjectListParams {
  window?: string
  start?: string
  end?: string
}

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

  async getProjects(params?: ProjectListParams) {
    const qs = buildQueryString(params as Record<string, unknown>)
    return apiRequest(`/config/projects${qs}`)
  },

  async getProject(slug: string, params?: ProjectListParams) {
    const qs = buildQueryString(params as Record<string, unknown>)
    return apiRequest(`/config/projects/${slug}${qs}`)
  },

  async createProject(data: unknown) {
    return apiRequest('/config/projects', { method: 'POST', body: JSON.stringify(data) })
  },
}