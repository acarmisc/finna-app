import { render, screen } from '@testing-library/react'

import { ProviderBadge } from './provider-badge'

describe('ProviderBadge Component', () => {
  it('should render with azure provider', () => {
    render(<ProviderBadge provider="azure" />)
    const badge = screen.getByText('AZ')
    expect(badge).toBeInTheDocument()
  })

  it('should render with gcp provider', () => {
    render(<ProviderBadge provider="gcp" />)
    const badge = screen.getByText('GCP')
    expect(badge).toBeInTheDocument()
  })

  it('should render with llm provider', () => {
    render(<ProviderBadge provider="llm" />)
    const badge = screen.getByText('LLM')
    expect(badge).toBeInTheDocument()
  })

  it('should render with aws provider', () => {
    render(<ProviderBadge provider="aws" />)
    const badge = screen.getByText('AWS')
    expect(badge).toBeInTheDocument()
  })

  it('should render with ecb provider', () => {
    render(<ProviderBadge provider="ecb" />)
    const badge = screen.getByText('FX')
    expect(badge).toBeInTheDocument()
  })

  it('should render unknown provider with uppercase first two chars', () => {
    render(<ProviderBadge provider="openai" />)
    const badge = screen.getByText('OP')
    expect(badge).toBeInTheDocument()
  })

  it('should render with fallback for unknown provider', () => {
    render(<ProviderBadge provider="unknown" />)
    const badge = screen.getByText('UN')
    expect(badge).toBeInTheDocument()
  })

  it('should render empty fallback when provider is empty string', () => {
    render(<ProviderBadge provider="" />)
    const badge = screen.getByText('??')
    expect(badge).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<ProviderBadge provider="azure" className="custom-class" />)
    const badge = screen.getByText('AZ')
    expect(badge).toHaveClass('custom-class')
  })

  it('should render with large size', () => {
    render(<ProviderBadge provider="gcp" size="lg" />)
    const badge = screen.getByText('GCP')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('prov-lg')
  })

  it('should apply provider class for styling', () => {
    render(<ProviderBadge provider="azure" />)
    const badge = screen.getByText('AZ')
    expect(badge).toHaveClass('prov')
    expect(badge).toHaveClass('azure')
  })
})
