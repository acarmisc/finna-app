import React from 'react'

interface StatCardProps {
  label: string
  value: string | number
  unit?: string
  delta?: string
  deltaDir?: 'up' | 'down' | 'flat'
  meta?: string
  accent?: string
  loading?: boolean
  className?: string
}

export function StatCard({
  label,
  value,
  unit = 'USD',
  delta,
  deltaDir = 'flat',
  meta,
  accent = 'primary',
  loading = false,
  className,
}: StatCardProps) {
  if (loading) {
    return (
      <div className={`stat ${accent}${className ? ` ${className}` : ''}`}>
        <div className="stat-lbl">{label}</div>
        <div className="skel" style={{ width: '60%', height: 28, marginTop: 4 }} />
        <div className="skel" style={{ width: '40%', height: 12, marginTop: 10 }} />
      </div>
    )
  }

  const arrow = deltaDir === 'up' ? '▲' : deltaDir === 'down' ? '▼' : '—'

  return (
    <div className={`stat ${accent}${className ? ` ${className}` : ''}`}>
      <div className="stat-lbl">{label}</div>
      <div className="stat-val">
        <span className="num">{value}</span>
        {unit && <span className="ccy">{unit}</span>}
      </div>
      {(delta || meta) && (
        <div className="stat-meta">
          {delta && (
            <span className={`delta ${deltaDir}`}>
              {arrow} {delta}
            </span>
          )}
          {meta && <span>· {meta}</span>}
        </div>
      )}
    </div>
  )
}

export default StatCard