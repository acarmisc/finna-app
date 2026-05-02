import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'

export type Theme = 'dark' | 'light' | 'system'

interface ThemeContextType {
  theme: Theme
  resolvedTheme: 'dark' | 'light'
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const SYSTEM_PREFERENCE_KEY = 'finna_theme_system'
const STORED_THEME_KEY = 'finna_theme'

const detectSystemTheme = (): 'dark' | 'light' => {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = localStorage.getItem(STORED_THEME_KEY) as Theme
    return stored || 'system'
  })

  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>(() => {
    if (theme === 'system') return detectSystemTheme()
    return theme
  })

  useEffect(() => {
    const root = document.documentElement
    const effectiveTheme = theme === 'system' ? detectSystemTheme() : theme
    setResolvedTheme(effectiveTheme)
    
    if (effectiveTheme === 'dark') {
      root.setAttribute('data-theme', 'dark')
      root.classList.remove('light')
      root.classList.add('dark')
    } else {
      root.setAttribute('data-theme', 'light')
      root.classList.remove('dark')
      root.classList.add('light')
    }
  }, [theme])

  useEffect(() => {
    if (theme !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const newTheme = media.matches ? 'dark' : 'light'
      setResolvedTheme(newTheme)
      const root = document.documentElement
      if (newTheme === 'dark') {
        root.setAttribute('data-theme', 'dark')
        root.classList.remove('light')
        root.classList.add('dark')
      } else {
        root.setAttribute('data-theme', 'light')
        root.classList.remove('dark')
        root.classList.add('light')
      }
    }
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [theme])

  const handleSetTheme = useCallback((newTheme: Theme) => {
    setTheme(newTheme)
    localStorage.setItem(STORED_THEME_KEY, newTheme)
  }, [])

  const handleToggleTheme = useCallback(() => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    handleSetTheme(newTheme)
  }, [theme, handleSetTheme])

  const value: ThemeContextType = {
    theme,
    resolvedTheme,
    setTheme: handleSetTheme,
    toggleTheme: handleToggleTheme,
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
