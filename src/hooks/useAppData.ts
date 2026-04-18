import { useState, useEffect, useCallback } from 'react';
import type { AppData } from '../types';
import { FINNA_DATA } from '../data';
import { apiGet } from '../api/client';
import type { CloudConfig, ExtractorRun, ExtractorHealth } from '../api/types';

export function useAppData(): {
  data: AppData;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  configs: CloudConfig[];
  runs: ExtractorRun[];
  health: ExtractorHealth[];
} {
  const [appData] = useState<AppData>(FINNA_DATA);
  const [configs, setConfigs] = useState<CloudConfig[]>([]);
  const [runs, setRuns] = useState<ExtractorRun[]>([]);
  const [health, setHealth] = useState<ExtractorHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick(t => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet<CloudConfig[]>('/config').catch(() => []),
      apiGet<ExtractorRun[]>('/extractors/status').catch(() => []),
      apiGet<ExtractorHealth[]>('/extractors/health').catch(() => []),
    ])
      .then(([c, r, h]) => {
        if (!cancelled) {
          setConfigs(c);
          setRuns(r);
          setHealth(h);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [tick]);

  return { data: appData, loading, error, refetch, configs, runs, health };
}