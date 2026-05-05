import React from 'react'
import { ProviderBadge } from './provider-badge'

interface HBarItem {
  name: string
  value: number
  provider?: string
  [key: string]: unknown
}

interface HBarListProps {
  items: HBarItem[]
  max?: number
  colorFor?: (item: HBarItem) => string
  className?: string
}

export function HBarList({ items, max, colorFor, className }: HBarListProps) {
  const m = max ?? Math.max(...items.map(i => i.value), 1)

  return (
    <div className={`stack${className ? ` ${className}` : ''}`} style={{ gap: 10 }}>
      {items.map((it, i) => (
        <div
          key={i}
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr auto',
            gap: 10,
            alignItems: 'center',
            fontSize: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, overflow: 'hidden' }}>
            {it.provider && <ProviderBadge provider={it.provider} size="sm" />}
            <span className="mono truncate" style={{ color: 'var(--fg)' }}>
              {it.name}
            </span>
          </div>
          <div
            style={{
              position: 'relative',
              height: 8,
              background: 'var(--surface-3)',
              border: '1px solid var(--border)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: `${(it.value / m) * 100}%`,
                background: colorFor ? colorFor(it) : 'var(--primary)',
              }}
            />
          </div>
          <div
            className="mono num"
            style={{ color: 'var(--fg)', minWidth: 80, textAlign: 'right' }}
          >
            {money(it.value)}
          </div>
        </div>
      ))}
    </div>
  )
}

function money(n: number): string {
  if (n == null || isNaN(n)) return '—'
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default HBarList