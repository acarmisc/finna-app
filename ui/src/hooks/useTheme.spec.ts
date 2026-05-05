import { renderHook, act } from '@testing-library/react'
import { useThemeHook } from './useTheme'
import { useTheme } from '@/contexts/ThemeContext'
import * as React from 'react'

// Create mock functions for useTheme
const mockSetTheme = jest.fn()
const mockToggleTheme = jest.fn()

// Mock the ThemeContext
jest.mock('@/contexts/ThemeContext', () => ({
  ThemeContext: {
    Provider: ({ children }: { children: React.ReactNode }) => children,
  },
  useTheme: () => ({
    theme: 'system',
    resolvedTheme: 'dark',
    setTheme: mockSetTheme,
    toggleTheme: mockToggleTheme,
  }),
}))

describe('useThemeHook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should return the correct initial values', () => {
    const { result } = renderHook(() => useThemeHook())
    expect(result.current.theme).toBe('system')
    expect(result.current.resolvedTheme).toBe('dark')
    expect(typeof result.current.setTheme).toBe('function')
    expect(typeof result.current.toggleTheme).toBe('function')
  })

  it('should call setTheme from context when setTheme is called', () => {
    const { result } = renderHook(() => useThemeHook())
    act(() => {
      result.current.setTheme('light')
    })
    expect(mockSetTheme).toHaveBeenCalledWith('light')
  })

  it('should call toggleTheme from context when toggleTheme is called', () => {
    const { result } = renderHook(() => useThemeHook())
    act(() => {
      result.current.toggleTheme()
    })
    expect(mockToggleTheme).toHaveBeenCalled()
  })
})