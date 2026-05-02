import React, { createContext, useContext, useCallback } from 'react'
import { toast as sonnerToast, Toaster } from 'sonner'

export type ToastType = 'success' | 'error' | 'info' | 'warning' | 'loading'

interface ToastContextType {
  showToast: (message: string, type?: ToastType, options?: {
    description?: string
    action?: {
      label: string
      onClick: () => void
    }
  }) => void
  showSuccess: (message: string, options?: {
    description?: string
  }) => void
  showError: (message: string, options?: {
    description?: string
    action?: {
      label: string
      onClick: () => void
    }
  }) => void
  showInfo: (message: string, options?: {
    description?: string
  }) => void
  showWarning: (message: string, options?: {
    description?: string
  }) => void
  dismiss: (id: string | number) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

const TOAST_TYPES: Record<ToastType, (title: string, options?: any) => void> = {
  success: sonnerToast.success,
  error: sonnerToast.error,
  info: sonnerToast.info,
  warning: sonnerToast.warning,
  loading: (title, options) => sonnerToast.loading(title, options),
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const showToast = useCallback((message: string, type: ToastType = 'info', options?: {
    description?: string
    action?: {
      label: string
      onClick: () => void
    }
  }) => {
    TOAST_TYPES[type](message, {
      description: options?.description,
      action: options?.action && {
        label: options.action.label,
        onClick: options.action.onClick,
      },
    })
  }, [])

  const showSuccess = useCallback((message: string, options?: {
    description?: string
  }) => {
    showToast(message, 'success', options)
  }, [showToast])

  const showError = useCallback((message: string, options?: {
    description?: string
    action?: {
      label: string
      onClick: () => void
    }
  }) => {
    showToast(message, 'error', options)
  }, [showToast])

  const showInfo = useCallback((message: string, options?: {
    description?: string
  }) => {
    showToast(message, 'info', options)
  }, [showToast])

  const showWarning = useCallback((message: string, options?: {
    description?: string
  }) => {
    showToast(message, 'warning', options)
  }, [showToast])

  const dismiss = useCallback((id: string | number) => {
    sonnerToast.dismiss(id)
  }, [])

  const value: ToastContextType = {
    showToast,
    showSuccess,
    showError,
    showInfo,
    showWarning,
    dismiss,
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster position="top-right" />
    </ToastContext.Provider>
  )
}

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
