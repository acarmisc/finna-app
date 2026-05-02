import { useCallback } from 'react'
import { useTheme } from '@/contexts/ThemeContext'

export interface ThemeHook {
  theme: 'dark' | 'light' | 'system'
  resolvedTheme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light' | 'system') => void
  toggleTheme: () => void
}

export const useThemeHook = (): ThemeHook => {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme()

  return {
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
  }
}
