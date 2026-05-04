// Costs API client
import { apiRequest, buildQueryString } from './request'

export const costsClient = {
  async getCosts(params?: Record<string, unknown>) {
    return apiRequest(`/costs${buildQueryString(params)}`)
  },

  async getCostTotals(params?: Record<string, unknown>) {
    return apiRequest(`/costs/totals${buildQueryString(params)}`)
  },

  async getDailyCosts(params?: Record<string, unknown>) {
    return apiRequest(`/costs/daily${buildQueryString(params)}`)
  },

  async getCostsBySku(params?: Record<string, unknown>) {
    return apiRequest(`/costs/by-sku${buildQueryString(params)}`)
  },
}