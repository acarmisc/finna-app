import { render, screen } from '@testing-library/react'

import { Badge } from './badge'

describe('Badge Component', () => {
  it('should render badge with default variant', () => {
    render(<Badge>Badge text</Badge>)
    expect(screen.getByText('Badge text')).toBeInTheDocument()
  })

  it('should render badge with secondary variant', () => {
    render(<Badge variant="secondary">Secondary</Badge>)
    expect(screen.getByText('Secondary')).toBeInTheDocument()
  })

  it('should render badge with destructive variant', () => {
    render(<Badge variant="destructive">Destructive</Badge>)
    expect(screen.getByText('Destructive')).toBeInTheDocument()
  })

  it('should render badge with outline variant', () => {
    render(<Badge variant="outline">Outline</Badge>)
    expect(screen.getByText('Outline')).toBeInTheDocument()
  })

  it('should render badge with ghost variant', () => {
    render(<Badge variant="ghost">Ghost</Badge>)
    expect(screen.getByText('Ghost')).toBeInTheDocument()
  })

  it('should render badge with link variant', () => {
    render(<Badge variant="link">Link</Badge>)
    expect(screen.getByText('Link')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<Badge className="custom-badge">Custom</Badge>)
    expect(screen.getByText('Custom')).toHaveClass('custom-badge')
  })
})
