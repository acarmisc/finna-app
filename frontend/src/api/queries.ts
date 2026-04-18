import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiPost, ApiError } from './client';
import type { CloudConfig, ExtractorRun, ExtractorHealth } from './types';

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useApiQuery<T>(path: string, defaultValue: T | null = null): QueryState<T> {
  const [data, setData] = useState<T | null>(defaultValue);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick(t => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGet<T>(path)
      .then(res => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: ApiError) => {
        if (!cancelled) {
          setError(err.detail || err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [path, tick]);

  return { data, loading, error, refetch };
}

export function useConfigs() {
  return useApiQuery<CloudConfig[]>('/config', []);
}

export function useConfig(id: string | undefined) {
  return useApiQuery<CloudConfig>(id ? `/config/${id}` : '', id ? null : undefined as any);
}

export function useExtractorRuns() {
  return useApiQuery<ExtractorRun[]>('/extractors/status', []);
}

export function useExtractorHealth() {
  return useApiQuery<ExtractorHealth[]>('/extractors/health', []);
}

export function useRunExtractor() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runExtractor = useCallback(async (provider: string, configId?: string, extractorType?: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiPost<ExtractorRun>('/extractors/run', {
        provider,
        config_id: configId || null,
        extractor_type: extractorType || null,
      });
      setSubmitting(false);
      return res;
    } catch (err: any) {
      setError(err.detail || err.message);
      setSubmitting(false);
      throw err;
    }
  }, []);

  return { runExtractor, submitting, error };
}
