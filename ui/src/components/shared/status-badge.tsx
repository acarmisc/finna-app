import React from 'react'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
  className?: string
}

const STATUS_MAP: Record<string, { cls: string; text: string; pulse?: boolean }> = {
  started:   { cls: 'ghost-warning', text: 'STARTED' },
  running:   { cls: 'solid-accent',  text: 'RUNNING', pulse: true },
  completed: { cls: 'ghost-accent',  text: 'COMPLETED' },
  failed:    { cls: 'ghost-danger',  text: 'FAILED' },
  cancelled: { cls: 'ghost-muted',   text: 'CANCELLED' },
  ok:        { cls: 'ghost-accent',  text: 'OK' },
  err:       { cls: 'ghost-danger',  text: 'ERROR' },
  warn:      { cls: 'ghost-warning', text: 'WARN' },
  firing:    { cls: 'solid-danger',  text: 'FIRING', pulse: true },
  ack:       { cls: 'ghost-warning', text: "ACK'D" },
  resolved:  { cls: 'ghost-accent',  text: 'RESOLVED' },
  pending:   { cls: 'ghost-muted',   text: 'PENDING' },
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const m = STATUS_MAP[status] || { cls: 'ghost-muted', text: status.toUpperCase() }
  return (
    <span className={cn(`badge ${m.cls}`, className)}>
      {m.pulse && <span className="dot pulse" />}
      {m.text}
    </span>
  )
}

export default StatusBadge