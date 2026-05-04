import React from 'react'
import { cn } from '@/lib/cn'

type BadgeVariant = 'provider' | 'status' | 'severity'

interface BadgeProps {
  variant?: BadgeVariant
  value: string
  size?: 'sm' | 'lg'
  className?: string
}

// Provider configuration
const PROVIDER_LABEL_MAP: Record<string, string> = {
  azure: 'AZ',
  gcp: 'GCP',
  llm: 'LLM',
  aws: 'AWS',
  ecb: 'FX',
}

// Status configuration
const STATUS_CONFIG: Record<string, { cls: string; text: string; pulse?: boolean }> = {
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

// Severity configuration
const SEVERITY_CONFIG: Record<string, { cls: string; text: string }> = {
  critical: { cls: 'solid-danger', text: 'CRITICAL' },
  high:    { cls: 'ghost-danger', text: 'HIGH' },
  medium:  { cls: 'ghost-warning', text: 'MEDIUM' },
  low:     { cls: 'ghost-muted', text: 'LOW' },
}

export function Badge({ variant = 'status', value, size, className }: BadgeProps) {
  const baseClasses = 'badge'

  if (variant === 'provider') {
    const label = PROVIDER_LABEL_MAP[value] || value?.toUpperCase().slice(0, 2) || '??'
    return (
      <span className={cn(baseClasses, `prov ${value}`, size === 'lg' ? 'prov-lg' : '', className)}>
        {label}
      </span>
    )
  }

  if (variant === 'severity') {
    const cfg = SEVERITY_CONFIG[value] || { cls: 'ghost-muted', text: value.toUpperCase() }
    return (
      <span className={cn(baseClasses, cfg.cls, className)}>
        {cfg.text}
      </span>
    )
  }

  // Default: status variant
  const cfg = STATUS_CONFIG[value] || { cls: 'ghost-muted', text: value.toUpperCase() }
  return (
    <span className={cn(baseClasses, cfg.cls, className)}>
      {cfg.pulse && <span className="dot pulse" />}
      {cfg.text}
    </span>
  )
}

export default Badge