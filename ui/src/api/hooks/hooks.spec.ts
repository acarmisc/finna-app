import { renderHook, act, waitFor } from '@testing-library/react'
import { useCosts, useCostTotals, useLogin } from '@/api/hooks'
import { getApiClient } from '@/services/apiClient'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as React from 'react'

// Mock the API client factory function
const mockApiClientInstance = {
  getCosts: jest.fn(),
  getCostTotals: jest.fn(),
  login: jest.fn()
}

jest.mock('@/services/apiClient', () => ({
  getApiClient: jest.fn(() => mockApiClientInstance)
}))

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    React.createElement(QueryClientProvider, { client: queryClient }, children)
  )
}

describe('API Hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('useCosts', () => {
    it('should call getCosts with correct parameters', async () => {
      const mockData = { items: [], total: 0 }
      mockApiClientInstance.getCosts.mockResolvedValue({ data: mockData, status: 200 })

      const { result } = renderHook(
        () => useCosts(),
        { wrapper: createWrapper() }
      )
      
      // Wait for the query to settle
      await waitFor(() => result.current.isSuccess || result.current.isError)
      
      expect(mockApiClientInstance.getCosts).toHaveBeenCalledWith(undefined)
    })

    it('should call getCosts with params', async () => {
      const mockData = { items: [], total: 0 }
      const params = { provider: 'azure', project: 'test' }
      mockApiClientInstance.getCosts.mockResolvedValue({ data: mockData, status: 200 })

      const { result } = renderHook(
        () => useCosts(params),
        { wrapper: createWrapper() }
      )
      
      // Wait for the query to settle
      await waitFor(() => result.current.isSuccess || result.current.isError)
      
      expect(mockApiClientInstance.getCosts).toHaveBeenCalledWith(params)
    })
  })

  describe('useCostTotals', () => {
    it('should call getCostTotals with correct parameters', async () => {
      const mockData = { azure: 100, gcp: 50, llm: 25, total: 175 }
      mockApiClientInstance.getCostTotals.mockResolvedValue({ data: mockData, status: 200 })

      const { result } = renderHook(
        () => useCostTotals(),
        { wrapper: createWrapper() }
      )
      
      // Wait for the query to settle
      await waitFor(() => result.current.isSuccess || result.current.isError)
      
      expect(mockApiClientInstance.getCostTotals).toHaveBeenCalledWith(undefined)
    })
  })

  describe('useLogin', () => {
    it('should call login with correct parameters', async () => {
      const mockToken = 'fake-jwt-token'
      mockApiClientInstance.login.mockResolvedValue({ data: { token: mockToken }, status: 200 })

      const { result } = renderHook(
        () => useLogin(),
        { wrapper: createWrapper() }
      )
      
      await act(async () => {
        await result.current.mutate({ username: 'test', password: 'test' })
      })
      
      // Wait for the mutation to settle
      await waitFor(() => result.current.isSuccess || result.current.isError)
      
      expect(mockApiClientInstance.login).toHaveBeenCalledWith('test', 'test')
    })
  })
})