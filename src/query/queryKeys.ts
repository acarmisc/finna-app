type QueryKey = string | (string | number)[]

interface QueryKeys {
  auth: {
    me: QueryKey
    refresh: QueryKey
  }
  totals: (window: string) => QueryKey
  costs: (filters: Record<string, unknown>) => QueryKey
  projects: (filters: Record<string, unknown>) => QueryKey
  project: (slug: string) => QueryKey
  configs: () => QueryKey
  config: (id: string) => QueryKey
  runs: (filters: Record<string, unknown>) => QueryKey
  run: (id: string) => QueryKey
  alerts: (filters: Record<string, unknown>) => QueryKey
  alert: (id: string) => QueryKey
  stats: () => QueryKey
  settings: {
    profile: QueryKey
    apiKeys: QueryKey
    notifications: QueryKey
    preferences: QueryKey
  }
}

export const queryKeys: QueryKeys = {
  auth: {
    me: ['auth', 'me'],
    refresh: ['auth', 'refresh'],
  },
  totals: (window: string) => ['totals', window] as QueryKey,
  costs: (filters: Record<string, unknown>) => ['costs', 'list', filters] as QueryKey,
  projects: (filters: Record<string, unknown>) => ['projects', 'list', filters] as QueryKey,
  project: (slug: string) => ['project', slug] as QueryKey,
  configs: () => ['configs', 'list'] as QueryKey,
  config: (id: string) => ['config', id] as QueryKey,
  runs: (filters: Record<string, unknown>) => ['runs', 'list', filters] as QueryKey,
  run: (id: string) => ['run', id] as QueryKey,
  alerts: (filters: Record<string, unknown>) => ['alerts', 'list', filters] as QueryKey,
  alert: (id: string) => ['alert', id] as QueryKey,
  stats: () => ['alerts', 'stats'] as QueryKey,
  settings: {
    profile: ['settings', 'profile'] as QueryKey,
    apiKeys: ['settings', 'api-keys'] as QueryKey,
    notifications: ['settings', 'notifications'] as QueryKey,
    preferences: ['settings', 'preferences'] as QueryKey,
  },
}

export default queryKeys
