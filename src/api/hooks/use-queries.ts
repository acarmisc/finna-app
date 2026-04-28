import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'
import {
  DashboardTotalsSchema,
  DailyCostSchema,
  TopProjectSchema,
  ExtractorRunSchema,
  ProjectSchema,
  CostRecordSchema,
  CostBySkuGroupSchema,
  AlertStatsSchema,
  AlertSchema,
  CloudConfigSchema,
  RunHistoryRecordSchema,
  DataSourceSchema,
  UserProfileSchema,
  TokenResponseSchema,
} from './schemas'

// --- Auth ---
export function useLogin() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const res = await apiClient.post('/auth/login', credentials)
      return TokenResponseSchema.parse(res.data)
    },
    onSuccess: (data) => {
      // Token is stored by interceptor from auth store
      queryClient.clear()
    },
  })
}

// --- Dashboard ---
export function useDashboardData(range: string = 'mtd', enabled = true) {
  return useQuery({
    queryKey: ['dashboard', range],
    queryFn: async () => {
      const [totals, daily, runs] = await Promise.all([
        apiClient.get(`/dashboard/totals?range=${range}`),
        apiClient.get(`/dashboard/daily?range=${range}`),
        apiClient.get('/runs/history?limit=5'),
      ])
      return {
        totals: DashboardTotalsSchema.parse(totals.data),
        daily: DailyCostSchema.parse(daily.data),
        runs: z.array(ExtractorRunSchema).parse(runs.data),
      }
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 min
  })
}

export function useTopProjects(range: string = 'mtd') {
  return useQuery({
    queryKey: ['projects', 'top', range],
    queryFn: async () => {
      const res = await apiClient.get(`/projects/top?range=${range}&limit=5`)
      return z.array(TopProjectSchema).parse(res.data)
    },
  })
}

// --- Projects ---
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await apiClient.get('/projects')
      return z.array(ProjectSchema).parse(res.data)
    },
    staleTime: 2 * 60 * 1000,
  })
}

export function useProjectBySlug(slug: string) {
  return useQuery({
    queryKey: ['project', slug],
    queryFn: async () => {
      const res = await apiClient.get(`/projects/${slug}`)
      return ProjectSchema.extend({
        skus: z.array(z.object({
          sku: z.string(),
          mtd: z.number(),
          prev: z.number(),
          delta: z.number(),
        })),
      }).parse(res.data)
    },
    enabled: !!slug,
  })
}

// --- Costs ---
export function useCosts(filters: { providers?: string[]; sku?: string } = {}) {
  const params = new URLSearchParams()
  if (filters.providers?.length) {
    filters.providers.forEach(p => params.append('provider', p))
  }
  if (filters.sku) params.append('sku', filters.sku)
  
  return useQuery({
    queryKey: ['costs', filters],
    queryFn: async () => {
      const res = await apiClient.get(`/costs?${params}`)
      return z.array(CostRecordSchema).parse(res.data)
    },
  })
}

export function useCostsBySku(filters: { providers?: string[] } = {}) {
  const params = new URLSearchParams()
  if (filters.providers?.length) {
    filters.providers.forEach(p => params.append('provider', p))
  }
  
  return useQuery({
    queryKey: ['costs', 'bySku', filters],
    queryFn: async () => {
      const res = await apiClient.get(`/costs/by-sku?${params}`)
      return z.array(CostBySkuGroupSchema).parse(res.data)
    },
  })
}

export function useDailyCosts(providers: string[] = ['azure', 'gcp', 'llm']) {
  return useQuery({
    queryKey: ['costs', 'daily', providers],
    queryFn: async () => {
      const params = providers.map(p => `provider=${p}`).join('&')
      const res = await apiClient.get(`/costs/daily?${params}`)
      return DailyCostSchema.parse(res.data)
    },
    enabled: providers.length > 0,
  })
}

// --- Alerts ---
export function useAlerts() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: async () => {
      const res = await apiClient.get('/alerts')
      return z.array(AlertSchema).parse(res.data)
    },
    staleTime: 60 * 1000,
  })
}

export function useAlertStats() {
  return useQuery({
    queryKey: ['alerts', 'stats'],
    queryFn: async () => {
      const res = await apiClient.get('/alerts/stats')
      return AlertStatsSchema.parse(res.data)
    },
  })
}

// --- Cloud Configs ---
export function useConfigs() {
  return useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const res = await apiClient.get('/config')
      return z.array(CloudConfigSchema).parse(res.data)
    },
  })
}

export function useCreateConfig() {
  return useMutation({
    mutationFn: async (config: { name: string; provider: string; credential_type: string; config: Record<string, unknown> }) => {
      const res = await apiClient.post('/config', config)
      return CloudConfigSchema.parse(res.data)
    },
  })
}

export function useTestConfig() {
  return useMutation({
    mutationFn: async (configId: string) => {
      const res = await apiClient.post(`/config/${configId}/test`)
      return res.data
    },
  })
}

export function useDeleteConfig() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (configId: string) => {
      await apiClient.delete(`/config/${configId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configs'] })
    },
  })
}

// --- Run History ---
export function useRunHistory(provider?: string) {
  return useQuery({
    queryKey: ['runs', 'history', provider],
    queryFn: async () => {
      const url = provider 
        ? `/runs/history?provider=${provider}`
        : '/runs/history'
      const res = await apiClient.get(url)
      return z.array(RunHistoryRecordSchema).parse(res.data)
    },
  })
}

// --- Data Sources ---
export function useDataSources() {
  return useQuery({
    queryKey: ['data', 'sources'],
    queryFn: async () => {
      const res = await apiClient.get('/extractors')
      return z.array(DataSourceSchema).parse(res.data)
    },
  })
}

// --- Settings ---
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const res = await apiClient.get('/auth/profile')
      return UserProfileSchema.parse(res.data)
    },
  })
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: async (profile: Record<string, string>) => {
      const res = await apiClient.put('/auth/profile', profile)
      return UserProfileSchema.parse(res.data)
    },
  })
}

// Import z for inline schemas
import { z } from 'zod/v4'
