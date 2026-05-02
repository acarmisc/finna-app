import React from 'react'

interface DialogProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  actions?: React.ReactNode
  className?: string
}

export function Dialog({ open, onClose, title, children, actions, className }: DialogProps) {
  if (!open) return null

  return (
    <div className="dlg-scrim" onClick={onClose}>
      <div className={`dlg${className ? ` ${className}` : ''}`} onClick={e => e.stopPropagation()}>
        <div className="dlg-hd">{title}</div>
        <div className="dlg-bd">{children}</div>
        {actions && <div className="dlg-ft">{actions}</div>}
      </div>
    </div>
  )
}

export default Dialog