import React from 'react';

interface BadgeProps {
  tone?: 'ok' | 'warn' | 'err' | 'info' | 'neu';
  children: React.ReactNode;
  dot?: boolean;
}

export function Badge({ tone = 'neu', children, dot }: BadgeProps) {
  return (
    <span className={`fn-badge fn-b-${tone}`}>
      {dot && <span className="fn-badge-dot" />}
      {children}
    </span>
  );
}
