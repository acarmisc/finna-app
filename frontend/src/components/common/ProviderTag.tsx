import React from 'react';
import type { Provider } from '../../types';

const PROVIDER_COLORS: Record<string, string> = {
  gcp: '#4285F4',
  azure: '#0078D4',
  aws: '#FF9900',
  llm: 'oklch(0.55 0.18 300)',
  ecb: 'var(--fg-muted)',
};

const PROVIDER_LABELS: Record<string, string> = {
  gcp: 'GCP',
  azure: 'Azure',
  aws: 'AWS',
  llm: 'LLM',
  ecb: 'ECB',
};

interface ProviderDotProps {
  p: Provider | string;
}

export function ProviderDot({ p }: ProviderDotProps) {
  const color = PROVIDER_COLORS[p] || '#888';
  return <span className="fn-dot" style={{ background: color }} />;
}

interface ProviderTagProps {
  p: Provider | string;
  mono?: boolean;
}

export function ProviderTag({ p, mono }: ProviderTagProps) {
  const label = PROVIDER_LABELS[p] || p;
  return (
    <span className="fn-provtag">
      <ProviderDot p={p} />
      <span className={mono ? 'mono' : ''}>{label}</span>
    </span>
  );
}
