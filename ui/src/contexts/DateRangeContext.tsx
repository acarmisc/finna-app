import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

type DateRangeType = 'mtd' | '7d' | '30d' | '90d' | 'custom'

interface DateRangeState {
  window: DateRangeType
  start: string
  end: string
}

const RANGE_DAYS: Record<string, { start: number; end: number }> = {
  '7d': { start: -6, end: 0 },
  '30d': { start: -29, end: 0 },
  '90d': { start: -89, end: 0 },
}

const getRangeFromWindow = (window: string, today: Date = new Date()): { start: string; end: string } => {
  if (window === 'mtd') {
    const start = new Date(today.getFullYear(), today.getMonth(), 1)
    return {
      start: start.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0],
    }
  }

  const days = RANGE_DAYS[window]
  if (days) {
    const end = today
    const start = new Date(today)
    start.setDate(today.getDate() + days.start)
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    }
  }

  return { start: '', end: '' }
}

const parseCustomRange = (params: URLSearchParams): { start: string; end: string } | null => {
  const start = params.get('start')
  const end = params.get('end')
  if (start && end) {
    const s = new Date(start)
    const e = new Date(end)
    if (!isNaN(s.getTime()) && !isNaN(e.getTime()) && e >= s) {
      return { start, end }
    }
  }
  return null
}

interface DateRangeContextType {
  state: DateRangeState
  setRange: (range: string) => void
  setCustomRange: (range: { start: string; end: string }) => void
  resetRange: () => void
}

const DateRangeContext = createContext<DateRangeContextType | undefined>(undefined)

export const DateRangeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [window, setWindow] = useState<DateRangeType>(() => {
    const w = searchParams.get('window') as DateRangeType
    return (w && ['mtd', '7d', '30d', '90d', 'custom'].includes(w)) ? w : 'mtd'
  })
  const [customRange, setCustomRange] = useState<{ start: string; end: string } | null>(null)

  useEffect(() => {
    const parsedCustom = parseCustomRange(searchParams)
    if (parsedCustom) {
      setCustomRange(parsedCustom)
      setWindow('custom')
    }
  }, [searchParams])

  const range = window === 'custom' && customRange ? customRange : getRangeFromWindow(window)

  const updateURL = useCallback((win: string, rangeData: { start: string; end: string }) => {
    const params = new URLSearchParams()
    params.set('window', win)
    if (rangeData.start) params.set('start', rangeData.start)
    if (rangeData.end) params.set('end', rangeData.end)
    setSearchParams(params, { replace: true })
  }, [setSearchParams])

  const handleSetRange = useCallback((win: string) => {
    const rangeType = win as DateRangeType
    setWindow(rangeType)
    if (rangeType === 'custom') return
    const newRange = getRangeFromWindow(rangeType)
    updateURL(rangeType, newRange)
  }, [updateURL])

  const handleSetCustomRange = useCallback((range: { start: string; end: string }) => {
    setCustomRange(range)
    updateURL('custom', range)
  }, [updateURL])

  const handleResetRange = useCallback(() => {
    setWindow('mtd')
    setCustomRange(null)
    updateURL('mtd', getRangeFromWindow('mtd'))
  }, [updateURL])

  const value: DateRangeContextType = {
    state: {
      window,
      start: range.start,
      end: range.end,
    },
    setRange: handleSetRange,
    setCustomRange: handleSetCustomRange,
    resetRange: handleResetRange,
  }

  return (
    <DateRangeContext.Provider value={value}>
      {children}
    </DateRangeContext.Provider>
  )
}

export const useDateRange = (): DateRangeContextType => {
  const context = useContext(DateRangeContext)
  if (!context) {
    throw new Error('useDateRange must be used within a DateRangeProvider')
  }
  return context
}

export default DateRangeContext
