import React from 'react'

interface CostDeltaCellProps {
  value: number | null
  showArrow?: boolean
  className?: string
}

export function CostDeltaCell({ value, showArrow = true, className }: CostDeltaCellProps) {
  if (value == null || isNaN(value)) {
    return <span className={`delta-flat mono num${className ? ` ${className}` : ''}`}>—</span>
  }

  const dir = value > 0.1 ? 'up' : value < -0.1 ? 'down' : 'flat'
  const arrow = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '—'
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''

  return (
    <span className={`delta-${dir} mono num${className ? ` ${className}` : ''}`}>
      {showArrow && <span style={{ marginRight: 4 }}>{arrow}</span>}
      {sign}{Math.abs(value).toFixed(1)}%
    </span>
  )
}

export default CostDeltaCell