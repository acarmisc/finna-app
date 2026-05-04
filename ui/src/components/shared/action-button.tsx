import React from 'react'
import { Button } from './Button'

interface ConfirmButtonProps {
  onClick: () => void
  disabled?: boolean
  pending?: boolean
  children?: React.ReactNode
  className?: string
}

export function ConfirmButton({ onClick, disabled, pending, children, className }: ConfirmButtonProps) {
  return (
    <Button
      variant="primary"
      bracket
      onClick={onClick}
      disabled={disabled || pending}
      className={className}
    >
      {pending ? 'saving…' : children || 'confirm'}
    </Button>
  )
}

interface CancelButtonProps {
  onClick: () => void
  children?: React.ReactNode
  className?: string
}

export function CancelButton({ onClick, children, className }: CancelButtonProps) {
  return (
    <Button
      variant="ghost"
      onClick={onClick}
      className={className}
    >
      {children || 'cancel'}
    </Button>
  )
}

interface DangerButtonProps {
  onClick: () => void
  icon?: string
  bracket?: boolean
  disabled?: boolean
  children?: React.ReactNode
  className?: string
}

export function DangerButton({ onClick, icon = 'trash-2', bracket, disabled, children, className }: DangerButtonProps) {
  return (
    <Button
      variant="danger"
      icon={icon}
      bracket={bracket}
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {children || 'delete'}
    </Button>
  )
}

interface AddButtonProps {
  onClick: () => void
  label?: string
  variant?: 'primary' | 'default'
  className?: string
}

export function AddButton({ onClick, label = 'add', variant = 'primary', className }: AddButtonProps) {
  return (
    <Button
      icon="plus"
      variant={variant}
      bracket
      onClick={onClick}
      className={className}
    >
      {label}
    </Button>
  )
}

export { Button }
export default Button