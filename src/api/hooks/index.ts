// API hooks for Finna Console
// Uses React Query with the existing apiClient
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApiClient, type APIClient } from '@/services/apiClient'
import {
  CostListResponse,
  CostTotalsResponse,
  CostDailyResponse,
  CostBySkuResponse,
  AlertListResponse,
  AlertStatsResponse,
  ExtractorListResponse,
  ProjectResponse,
  CloudConfigResponse,
} from '@/types/api'

// ============ Cost Hooks ============

export function useCosts(params?: {
  provider?: string
  project?: string
  startDate?: string
  endDate?: string
}) {
  return useQuery<CostListResponse, Error>({
    queryKey: ['costs', params],
    queryFn: async () => {
      const res = await getApiClient().getCosts(params)
      return res.data as CostListResponse
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useCostTotals(params?: { startDate?: string; endDate?: string }) {
  return useQuery<CostTotalsResponse, Error>({
    queryKey: ['costs', 'totals', params],
    queryFn: async () => {
      const res = await getApiClient().getCostTotals(params)
      return res.data as CostTotalsResponse
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useDailyCosts(params?: {
  startDate?: string
  endDate?: string
  provider?: string
}) {
  return useQuery<CostDailyResponse, Error>({
    queryKey: ['costs', 'daily', params],
    queryFn: async () => {
      const res = await getApiClient().getDailyCosts(params)
      return res.data as CostDailyResponse
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useCostsBySku(params?: { provider?: string; limit?: number }) {
  return useQuery<CostBySkuResponse, Error>({
    queryKey: ['costs', 'by-sku', params],
    queryFn: async () => {
      const res = await getApiClient().getCostsBySku(params)
      return res.data as CostBySkuResponse
    },
  })
}

// ============ Alert Hooks ============

export function useAlerts(params?: {
  status?: string
  severity?: string
  limit?: number
}) {
  return useQuery<AlertListResponse, Error>({
    queryKey: ['alerts', params],
    queryFn: async () => {
      const res = await getApiClient().getAlerts(params)
      return res.data as AlertListResponse
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useAlertStats() {
  return useQuery<AlertStatsResponse, Error>({
    queryKey: ['alerts', 'stats'],
    queryFn: async () => {
      const res = await getApiClient().getAlertStats()
      return res.data as AlertStatsResponse
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getApiClient().acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alerts', 'stats'] })
    },
  })
}

// ============ Project Hooks ============

export function useProjects() {
  return useQuery<ProjectResponse[], Error>({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await getApiClient().getProjects()
      return res.data as ProjectResponse[]
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useProject(slug: string) {
  return useQuery<ProjectResponse, Error>({
    queryKey: ['projects', slug],
    queryFn: async () => {
      const res = await getApiClient().getProject(slug)
      return res.data as ProjectResponse
    },
    enabled: !!slug,
  })
}

// ============ Config/Connection Hooks ============

export function useConnections() {
  return useQuery<CloudConfigResponse[], Error>({
    queryKey: ['connections'],
    queryFn: async () => {
      const res = await getApiClient().getConnections()
      return res.data as CloudConfigResponse[]
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useConnection(id: string) {
  return useQuery<CloudConfigResponse, Error>({
    queryKey: ['connections', id],
    queryFn: async () => {
      const res = await getApiClient().getConnection(id)
      return res.data as CloudConfigResponse
    },
    enabled: !!id,
  })
}

export function useTestConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getApiClient().testConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

export function useCreateConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<APIClient['createConnection']>[0]) =>
      getApiClient().createConnection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

export function useDeleteConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => getApiClient().deleteConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

// ============ Extractor Hooks ============

export function useExtractors(params?: { provider?: string; limit?: number }) {
  return useQuery<ExtractorListResponse, Error>({
    queryKey: ['extractors', params],
    queryFn: async () => {
      const res = await getApiClient().getExtractors(params)
      return res.data as ExtractorListResponse
    },
  })
}

export function useExtractorRuns(params?: { configId?: string; limit?: number }) {
  return useQuery<{ runs: unknown[]; total: number }, Error>({
    queryKey: ['extractor-runs', params],
    queryFn: async () => {
      const res = await getApiClient().getExtractorRuns(params)
      return res.data as { runs: unknown[]; total: number }
    },
    placeholderData: (previousData) => previousData,
  })
}

export function useTriggerExtractor() {
  return useMutation({
    mutationFn: (data: { config_id: string; extractor_type?: string }) =>
      getApiClient().triggerExtractor(data),
  })
}

// ============ Auth Hooks ============

export function useLogin() {
  return useMutation({
    mutationFn: (data: { username: string; password: string }) =>
      getApiClient().login(data.username, data.password),
  })
}

// ============ Dashboard Hooks ============

export function useDashboardStats(range?: 'mtd' | '7d' | '30d' | '90d') {
  return useQuery<{
    totals: { azure: number; gcp: number; llm: number; total: number }
    daily: Array<{ date: string; azure: number; gcp: number; llm: number }>
    alertStats: { firing: number; ack: number; resolved: number }
  }, Error>({
    queryKey: ['dashboard', 'stats', range],
    queryFn: async () => {
      const res = await getApiClient().getDashboardStats(range)
      return res.data as {
        totals: { azure: number; gcp: number; llm: number; total: number }
        daily: Array<{ date: string; azure: number; gcp: number; llm: number }>
        alertStats: { firing: number; ack: number; resolved: number }
      }
    },
    placeholderData: (previousData) => previousData,
  })
}