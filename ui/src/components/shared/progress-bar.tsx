import React from 'react'

interface ProgressBarProps {
  value: number
  max?: number
  size?: 'sm' | 'lg'
  stepped?: boolean
  segments?: number
  className?: string
}

export function ProgressBar({
  value,
  max = 100,
  size = 'sm',
  stepped = false,
  segments = 10,
  className,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const tone = pct >= 90 ? 'danger' : pct >= 70 ? 'warn' : ''

  if (stepped) {
    const filled = Math.round((pct / 100) * segments)
    return (
      <div className={`pbar-steps ${tone}${className ? ` ${className}` : ''}`}>
        {Array.from({ length: segments }).map((_, i) => (
          <span key={i} className={`seg ${i < filled ? 'on' : ''}`} />
        ))}
      </div>
    )
  }

  return (
    <div className={`pbar ${size === 'lg' ? 'pbar-lg' : ''} ${tone}${className ? ` ${className}` : ''}`}>
      <div className="fill" style={{ width: `${pct}%` }} />
    </div>
  )
}

export default ProgressBar