import React from 'react'
import { Icon } from './Icon'

interface EmptyStateProps {
  icon?: string
  title?: string
  message?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon = 'inbox', title, message, action, className }: EmptyStateProps) {
  return (
    <div className={`empty${className ? ` ${className}` : ''}`}>
      <div className="icon">
        <Icon name={icon} size={20} />
      </div>
      {title && (
        <div style={{ color: 'var(--fg)', fontFamily: 'JetBrains Mono, monospace', fontSize: 13, marginBottom: 4 }}>
          {title}
        </div>
      )}
      <div className="msg">{message}</div>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

export default EmptyState