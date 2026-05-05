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
        <h3 style={{ color: 'var(--fg)', marginBottom: 4, margin: 0 }}>
          {title}
        </h3>
      )}
      <div className="msg">{message}</div>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

export default EmptyState