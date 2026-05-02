import { render, screen } from '@testing-library/react'

import { StatCard } from './stat-card'

describe('StatCard Component', () => {
  it('should render stat card with label and value', () => {
    render(<StatCard label="Total Spend" value="1,234" />)
    expect(screen.getByText('Total Spend')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
  })

  it('should render with default USD unit', () => {
    render(<StatCard label="Cost" value="100" />)
    expect(screen.getByText('USD')).toBeInTheDocument()
  })

  it('should render with custom unit', () => {
    render(<StatCard label="Hours" value="50" unit="hrs" />)
    expect(screen.getByText('hrs')).toBeInTheDocument()
  })

  it('should render with delta and up direction', () => {
    render(<StatCard label="Spend" value="500" delta="10" deltaDir="up" />)
    expect(screen.getByText('▲ 10')).toBeInTheDocument()
  })

  it('should render with delta and down direction', () => {
    render(<StatCard label="Spend" value="500" delta="5" deltaDir="down" />)
    expect(screen.getByText('▼ 5')).toBeInTheDocument()
  })

  it('should render with delta and flat direction', () => {
    render(<StatCard label="Spend" value="500" delta="0" deltaDir="flat" />)
    expect(screen.getByText('— 0')).toBeInTheDocument()
  })

  it('should render with meta text', () => {
    render(<StatCard label="Spend" value="500" meta="vs last month" />)
    expect(screen.getByText(/vs last month/)).toBeInTheDocument()
  })

  it('should render delta and meta together', () => {
    render(<StatCard label="Spend" value="500" delta="10" deltaDir="up" meta="vs yesterday" />)
    expect(screen.getByText(/vs yesterday/)).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<StatCard label="Test" value="100" className="custom-class" />)
    const stat = screen.getByText('Test').closest('.stat')
    expect(stat?.className).toContain('custom-class')
  })

  it('should render with default primary accent', () => {
    render(<StatCard label="Test" value="100" />)
    const stat = screen.getByText('Test').closest('.stat')
    expect(stat?.className).toContain('primary')
  })

  it('should render with custom accent', () => {
    render(<StatCard label="Test" value="100" accent="success" />)
    const stat = screen.getByText('Test').closest('.stat')
    expect(stat?.className).toContain('success')
  })

  it('should render loading state', () => {
    render(<StatCard label="Loading Test" value="0" loading={true} />)
    expect(screen.getByText('Loading Test')).toBeInTheDocument()
  })

  it('should not render delta/meta when loading', () => {
    render(<StatCard label="Test" value="100" loading={true} delta="10%" deltaDir="up" meta="info" />)
    expect(screen.queryByText('10%')).not.toBeInTheDocument()
    expect(screen.queryByText('info')).not.toBeInTheDocument()
  })

  it('should render with numeric value', () => {
    render(<StatCard label="Count" value={42} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})
