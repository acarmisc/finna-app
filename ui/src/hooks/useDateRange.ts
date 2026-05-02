import { useDateRange } from '@/contexts/DateRangeContext'

export const useDateRangeParams = (): {
  range: string
  setRange: (range: string) => void
  customRange: { start: string; end: string } | null
  setCustomRange: (range: { start: string; end: string } | null) => void
} => {
  const { state, setRange, setCustomRange } = useDateRange()
  
  return {
    range: state.window,
    setRange: (range: string) => {
      setRange(range)
    },
    customRange: state.window === 'custom' ? { start: state.start, end: state.end } : null,
    setCustomRange: (range: { start: string; end: string } | null) => {
      if (range) {
        setCustomRange(range)
      } else {
        setRange('mtd')
      }
    },
  }
}
