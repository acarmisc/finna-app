import React, { createContext, useContext, useState, useCallback } from 'react'
import { Icon } from './Icon'

interface Toast {
  id: string
  tone: 'ok' | 'err' | 'warn' | 'info'
  msg: string
}

interface ToastContextType {
  push: (tone: Toast['tone'], msg: string) => void
}

const ToastCtx = createContext<ToastContextType>({ push: () => {} })

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])

  const push = useCallback((tone: Toast['tone'], msg: string) => {
    const id = Math.random().toString(36).slice(2)
    setItems(xs => [...xs, { id, tone, msg }])
    setTimeout(() => setItems(xs => xs.filter(t => t.id !== id)), 4200)
  }, [])

  const dismiss = useCallback((id: string) => {
    setItems(xs => xs.filter(t => t.id !== id))
  }, [])

  const iconMap = {
    ok: 'check-circle-2',
    err: 'x-circle',
    warn: 'alert-triangle',
    info: 'info',
  }

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="toasts">
        {items.map(t => (
          <div key={t.id} className={`toast ${t.tone}`}>
            <Icon name={iconMap[t.tone]} size={14} />
            <span>{t.msg}</span>
            <span className="close" onClick={() => dismiss(t.id)}>×</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function useToast() {
  return useContext(ToastCtx)
}

export default ToastProvider