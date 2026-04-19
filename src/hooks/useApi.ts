/**
 * Custom hooks for API data management
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { getApiClient, APIClient } from './apiClient';

// Types for data states
interface UseDataResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
}

interface UsePaginationResult<T> {
  items: T[];
  loading: boolean;
  error: Error | null;
  refresh: () => void;
  hasMore: boolean;
}

// Main hook for fetching data
export function useData<T>(key: string, fetchFn: () => Promise<T>, deps: unknown[] = []): UseDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchFn()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, deps);

  useEffect(() => {
    refresh();
  }, deps);

  return useMemo(() => ({ data, loading, error, refresh }), [data, loading, error, refresh]);
}

// Hook for lists with pagination
export function useList<T>(key: string, fetchFn: (page: number, limit: number) => Promise<{ items: T[]; total: number }>, limit: number = 50): UsePaginationResult<T> {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchFn(page, limit)
      .then(({ items, total }) => {
        setItems(items);
        setTotal(total);
        setError(null);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    refresh();
  }, [page, limit]);

  const hasMore = items.length < total;

  return useMemo(() => ({
    items,
    loading,
    error,
    refresh,
    hasMore,
  }), [items, loading, error, refresh, hasMore]);
}

// Hook for cost data with filtering
export function useCosts(params?: {
  provider?: string;
  project?: string;
  startDate?: string;
  endDate?: string;
}) {
  return useData('costs', async () => {
    const client = getApiClient();
    const response = await client.getCosts(params);
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch costs');
    }
    return response.data;
  }, [params]);
}

// Hook for alerts
export function useAlerts(params?: {
  status?: string;
  severity?: string;
  limit?: number;
}) {
  return useData('alerts', async () => {
    const client = getApiClient();
    const response = await client.getAlerts(params);
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch alerts');
    }
    return response.data;
  }, [params]);
}

// Hook for runs/extractors
export function useRuns(limit: number = 50) {
  return useData('runs', async () => {
    const client = getApiClient();
    const response = await client.getRuns(limit);
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch runs');
    }
    return response.data;
  }, [limit]);
}

// Hook for connections
export function useConnections() {
  return useData('connections', async () => {
    const client = getApiClient();
    const response = await client.getConnections();
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch connections');
    }
    return response.data;
  }, []);
}

// Hook for active alerts (for dashboard)
export function useActiveAlerts() {
  return useData('activeAlerts', async () => {
    const client = getApiClient();
    const response = await client.getActiveAlerts();
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch active alerts');
    }
    return response.data;
  }, []);
}

// Hook for dashboard summary
export function useDashboardSummary() {
  return useData('dashboardSummary', async () => {
    const client = getApiClient();
    const [costsRes, alertsRes, runsRes] = await Promise.all([
      client.getCostTotals(),
      client.getAlerts({ limit: 100 }),
      client.getRuns(5),
    ]);

    if (costsRes.error) throw new Error(costsRes.error.message);
    if (alertsRes.error) throw new Error(alertsRes.error.message);
    if (runsRes.error) throw new Error(runsRes.error.message);

    return {
      costs: costsRes.data,
      alerts: alertsRes.data,
      runs: runsRes.data,
    };
  }, []);
}

// Hook for daily costs (for chart)
export function useDailyCosts(params?: {
  startDate?: string;
  endDate?: string;
  provider?: string;
}) {
  return useData('dailyCosts', async () => {
    const client = getApiClient();
    const response = await client.getDailyCosts(params);
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch daily costs');
    }
    return response.data;
  }, [params]);
}

// Hook for cost breakdown by SKU
export function useCostsBySku(limit: number = 50) {
  return useData('costsBySku', async () => {
    const client = getApiClient();
    const response = await client.getCostsBySku(limit);
    if (response.error) {
      throw new Error(response.error.message || 'Failed to fetch costs by SKU');
    }
    return response.data;
  }, [limit]);
}
