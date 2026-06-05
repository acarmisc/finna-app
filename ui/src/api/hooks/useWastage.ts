// React Query hooks for the wastage feature
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest, buildQueryString } from '@/services/api/request'
import type {
  WastageFindingListResponse,
  WastageFindingListResponse as FindingDetail,
  WastageFilterParams,
  WastageRulesResponse,
  WastageScansResponse,
  WastageSummaryResponse,
} from '@/types/wastage'

// ============ Findings ============

export function useWastageFindings(params?: WastageFilterParams) {
  return useQuery<WastageFindingListResponse, Error>({
    queryKey: ['wastage', 'findings', params],
    queryFn: async () => {
      const res = await apiRequest<WastageFindingListResponse>(`/wastage${buildQueryString(params)}`)
      return (res.data ?? { data: [], total: 0, limit: 50, offset: 0, has_next: false, has_prev: false }) as WastageFindingListResponse
    },
    placeholderData: (prev) => prev,
  })
}

export function useWastageFinding(findingId: string) {
  return useQuery({
    queryKey: ['wastage', 'finding', findingId],
    queryFn: async () => {
      const res = await apiRequest(`/wastage/${findingId}`)
      return res.data
    },
    enabled: !!findingId,
  })
}

export function useWastageSummary() {
  return useQuery<WastageSummaryResponse, Error>({
    queryKey: ['wastage', 'summary'],
    queryFn: async () => {
      const res = await apiRequest<WastageSummaryResponse>('/wastage/summary')
      return (res.data ?? { categories: [], total_monthly_usd: 0, total_finding_count: 0 }) as WastageSummaryResponse
    },
    placeholderData: (prev) => prev,
  })
}

export function useWastageRules() {
  return useQuery<WastageRulesResponse, Error>({
    queryKey: ['wastage', 'rules'],
    queryFn: async () => {
      const res = await apiRequest<WastageRulesResponse>('/wastage/rules')
      return (res.data ?? { rules: [], count: 0 }) as WastageRulesResponse
    },
  })
}

export function useWastageScans() {
  return useQuery<WastageScansResponse, Error>({
    queryKey: ['wastage', 'scans'],
    queryFn: async () => {
      const res = await apiRequest<WastageScansResponse>('/wastage/scans')
      return (res.data ?? { scans: [], count: 0 }) as WastageScansResponse
    },
    placeholderData: (prev) => prev,
  })
}

// ============ Mutations ============

export function useAckFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (findingId: string) =>
      apiRequest(`/wastage/${findingId}/ack`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wastage'] })
    },
  })
}

export function useResolveFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (findingId: string) =>
      apiRequest(`/wastage/${findingId}/resolve`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wastage'] })
    },
  })
}

export function useIgnoreFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ findingId, reason }: { findingId: string; reason: string }) =>
      apiRequest(`/wastage/${findingId}/ignore`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wastage'] })
    },
  })
}

export function useTriggerScan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (provider: string) =>
      apiRequest('/wastage/scan', {
        method: 'POST',
        body: JSON.stringify({ provider }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wastage', 'scans'] })
    },
  })
}
