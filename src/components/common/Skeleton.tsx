import React from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 20, className = '', style }: SkeletonProps) {
  return (
    <div
      className={`fn-skeleton ${className}`}
      style={{
        width,
        height,
        background: 'var(--bg-accent, #f0f0f0)',
        borderRadius: 'var(--radius-sm, 4px)',
        animation: 'fn-pulse 1.5s ease-in-out infinite',
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

export function SkeletonBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 16 }}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton
          key={i}
          width={i === rows - 1 ? '40%' : '100%'}
          height={i === 0 ? 24 : 16}
        />
      ))}
    </div>
  );
}
