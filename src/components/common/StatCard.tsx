import React from 'react';
import { Icon } from './Icon';

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  delta?: string;
  tone?: 'up' | 'down' | 'flat';
  meta?: string;
  sparkline?: number[];
  onClick?: () => void;
}

export function StatCard({ label, value, delta, tone = 'flat', meta, sparkline, onClick }: StatCardProps) {
  return (
    <div className={`fn-stat ${onClick ? 'is-clickable' : ''}`} onClick={onClick}>
      <div className="fn-stat-row">
        <div className="fn-stat-lbl">{label}</div>
        {sparkline && <Sparkline data={sparkline} tone={tone} />}
      </div>
      <div className="fn-stat-val">{value}</div>
      {(delta || meta) && (
        <div className={`fn-stat-delta fn-${tone}`}>
          {delta && (
            <>
              <Icon
                name={tone === 'up' ? 'arrow-up-right' : tone === 'down' ? 'arrow-down-right' : 'minus'}
                size={12}
              />
              <span>{delta}</span>
            </>
          )}
          {meta && <span className="fn-stat-meta">{delta ? ' · ' : ''}{meta}</span>}
        </div>
      )}
    </div>
  );
}

interface SparklineProps {
  data: number[];
  tone?: 'up' | 'down' | 'flat';
}

export function Sparkline({ data, tone = 'flat' }: SparklineProps) {
  const w = 64, h = 22, pad = 1;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const rng = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = pad + (i * (w - pad * 2)) / (data.length - 1);
      const y = h - pad - ((v - min) / rng) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const color =
    tone === 'up' ? 'var(--danger)' : tone === 'down' ? 'var(--success)' : 'var(--fg-muted)';
  return (
    <svg className="fn-spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
