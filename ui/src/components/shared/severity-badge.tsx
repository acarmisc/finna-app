import React from 'react'

interface SeverityBadgeProps {
  severity: string
  className?: string
}

const SEVERITY_MAP: Record<string, string> = {
  critical: 'solid-danger',
  warning:  'solid-warning',
  info:     'ghost-primary',
  err:      'solid-danger',
  warn:     'solid-warning',
  ok:       'ghost-accent',
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const cls = SEVERITY_MAP[severity] || 'ghost-muted'
  return (
    <span className={`badge ${cls}${className ? ` ${className}` : ''}`}>
      {severity}
    </span>
  )
}

export default SeverityBadge