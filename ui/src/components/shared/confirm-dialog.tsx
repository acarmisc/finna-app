import React from 'react'
import { Button } from './Button'

interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'confirm',
  cancelLabel = 'cancel',
  variant = 'default',
}: ConfirmDialogProps) {
  return (
    <div className="dlg-scrim" onClick={onClose} style={{ display: open ? undefined : 'none' }}>
      <div className="dlg" onClick={e => e.stopPropagation()}>
        <div className="dlg-hd">{title}</div>
        <div className="dlg-bd">
          <p>{message}</p>
        </div>
        <div className="dlg-ft">
          <Button onClick={onClose} bracket>{cancelLabel}</Button>
          <Button
            variant={variant === 'danger' ? 'danger' : 'primary'}
            onClick={() => {
              onConfirm()
              onClose()
            }}
            bracket
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog