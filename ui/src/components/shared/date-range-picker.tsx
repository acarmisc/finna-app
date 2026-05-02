import React from 'react'

interface DateRangePickerProps {
  startDate: string
  endDate: string
  onStartChange: (date: string) => void
  onEndChange: (date: string) => void
  className?: string
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  className,
}: DateRangePickerProps) {
  return (
    <div className={`hstack${className ? ` ${className}` : ''}`}>
      <input
        type="date"
        className="inp"
        value={startDate}
        onChange={e => onStartChange(e.target.value)}
      />
      <span style={{ color: 'var(--fg-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
        →
      </span>
      <input
        type="date"
        className="inp"
        value={endDate}
        onChange={e => onEndChange(e.target.value)}
      />
    </div>
  )
}

export default DateRangePicker