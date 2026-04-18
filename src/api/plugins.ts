import { useState, useEffect, useCallback } from 'react';
import { apiGet, ApiError } from './client';

export interface PluginConfigField {
  name: string;
  label: string;
  type: string;  // text | password | select | checkbox
  required: boolean;
  default: string | number | boolean | null;
  placeholder: string;
  options: { value: string; label: string }[];
}

export interface PluginAuthMethod {
  id: string;
  label: string;
  sub: string;
}

export interface PluginInfo {
  type: string;
  provider: string;
  display_name: string;
  description: string;
  auth_methods: PluginAuthMethod[];
  config_fields: PluginConfigField[];
}

interface PluginState {
  plugins: PluginInfo[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePlugins(): PluginState {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick(t => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<PluginInfo[]>('/plugins')
      .then(res => {
        if (!cancelled) {
          setPlugins(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load plugins');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [tick]);

  return { plugins, loading, error, refetch };
}