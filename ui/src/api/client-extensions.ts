import { createRequest } from './client'

const getAuthClient = () => ({
  login: (username: string, password: string) => 
    createRequest<{ username: string; password: string }, { token: string }>('POST', '/auth/login', { username, password }),
})

export { getAuthClient }

export const getConfigClient = () => ({
  list: () => createRequest<void, { configs: any[] }>('GET', '/configs'),
  get: (id: string) => createRequest<void, any>('GET', `/configs/${id}`),
  create: (data: any) => createRequest('POST', '/configs', data),
  update: (id: string, data: any) => createRequest('PUT', `/configs/${id}`, data),
  delete: (id: string) => createRequest('DELETE', `/configs/${id}`),
  test: (data: any) => createRequest('POST', '/configs/test', data),
})

export const getAlertClient = () => ({
  list: (filters?: { status?: string; provider?: string; severity?: string }) => {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.provider) params.set('provider', filters.provider)
    if (filters?.severity) params.set('severity', filters.severity)
    return createRequest<void, { alerts: any[]; count: number; total: number }>('GET', `/alerts?${params.toString()}`)
  },
  ack: (id: string) => createRequest<void, { id: string; acknowledged: boolean }>('POST', `/alerts/${id}/ack`),
  silence: (id: string, duration: number = 3600) => 
    createRequest<{ duration: number }, { id: string; silenced: boolean }>('POST', `/alerts/${id}/silence`, { duration }),
  dismiss: (id: string) => createRequest<void, { success: boolean }>('DELETE', `/alerts/${id}`),
  stats: () => createRequest<void, { total: number; by_severity: Record<string, number>; by_provider: Record<string, number> }>('GET', '/alerts/stats'),
})

export const getSettingsClient = () => ({
  profile: () => createRequest<void, { id: string; email: string; name?: string; role: string; org_id: string; timezone: string; locale: string }>('GET', '/users/me'),
  updateProfile: (data: Partial<{ name?: string; timezone?: string; locale?: string }>) => 
    createRequest('PUT', '/users/me', data),
  preferences: () => createRequest<void, { theme: 'dark' | 'light' | 'system'; default_window: string; language: string }>('GET', '/users/me/preferences'),
  updatePreferences: (data: Partial<{ theme?: 'dark' | 'light' | 'system'; default_window?: string; language?: string }>) => 
    createRequest('PUT', '/users/me/preferences', data),
  apiKeys: () => createRequest<void, Array<{ id: string; name: string; created_at: string; scopes: string[] }>>('GET', '/api-keys'),
  createApiKey: (data: { name: string; scopes: string[] }) => 
    createRequest<{ name: string; scopes: string[] }, { id: string; key: string; name: string }>('POST', '/api-keys', data),
  deleteApiKey: (id: string) => createRequest<void, { success: boolean }>('DELETE', `/api-keys/${id}`),
})
