jest.mock('@/contexts/DateRangeContext')

import { renderHook, act } from '@testing-library/react'
import { useDateRangeParams } from './useDateRange'
import { useDateRange } from '@/contexts/DateRangeContext'
import * as React from 'react'

// Create mock functions for useDateRange
const mockSetRange = jest.fn()
const mockSetCustomRange = jest.fn()

// Mock the useDateRange hook from the mocked module
;(useDateRange as jest.Mock).mockImplementation(() => ({
  state: {
    window: 'mtd',
    start: '2024-01-01',
    end: '2024-01-31',
  },
  setRange: mockSetRange,
  setCustomRange: mockSetCustomRange,
}))

describe('useDateRangeParams', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should return the correct initial values', () => {
    const { result } = renderHook(() => useDateRangeParams())
    expect(result.current.range).toBe('mtd')
    expect(result.current.customRange).toBeNull() // Because window is 'mtd', not 'custom'
    expect(typeof result.current.setRange).toBe('function')
    expect(typeof result.current.setCustomRange).toBe('function')
  })

  it('should call setRange from context when setRange is called', () => {
    const { result } = renderHook(() => useDateRangeParams())
    act(() => {
      result.current.setRange('7d')
    })
    expect(mockSetRange).toHaveBeenCalledWith('7d')
  })

  it('should call setCustomRange from context when setCustomRange is called', () => {
    const { result } = renderHook(() => useDateRangeParams())
    const customRange = { start: '2024-01-01', end: '2024-01-31' }
    act(() => {
      result.current.setCustomRange(customRange)
    })
    expect(mockSetCustomRange).toHaveBeenCalledWith(customRange)
  })

  it('should call setRange with mtd when setCustomRange is called with null', () => {
    const { result } = renderHook(() => useDateRangeParams())
    act(() => {
      result.current.setCustomRange(null)
    })
    expect(mockSetRange).toHaveBeenCalledWith('mtd')
  })
})

describe('useDateRangeParams when window is custom', () => {
  // Mock the useDateRange hook for custom window
  const mockSetRangeCustom = jest.fn()
  const mockSetCustomRangeCustom = jest.fn()

  beforeEach(() => {
    ;(useDateRange as jest.Mock).mockImplementation(() => ({
      state: {
        window: 'custom',
        start: '2024-01-01',
        end: '2024-01-31',
      },
      setRange: mockSetRangeCustom,
      setCustomRange: mockSetCustomRangeCustom,
    }))
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('should return custom range when window is custom', () => {
    const { result } = renderHook(() => useDateRangeParams())
    expect(result.current.range).toBe('custom')
    expect(result.current.customRange).toEqual({ start: '2024-01-01', end: '2024-01-31' })
  })
})