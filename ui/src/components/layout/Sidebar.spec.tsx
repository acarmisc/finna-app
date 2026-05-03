import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Sidebar from './Sidebar'

describe('Sidebar Component', () => {
  it('should render sidebar with basic structure', () => {
    render(<Sidebar />)
    
    // Check that the sidebar renders
    const sidebar = screen.getByRole('complementary')
    expect(sidebar).toBeInTheDocument()
    
    // Check for the wordmark
    expect(screen.getByText('finna')).toBeInTheDocument()
    
    // Check for section headers
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Resources')).toBeInTheDocument()
    expect(screen.getByText('Monitoring')).toBeInTheDocument()
  })

  it('should render account information', () => {
    render(<Sidebar />)
    
    expect(screen.getByText('finops@acme.co')).toBeInTheDocument()
    expect(screen.getByText('API · healthy')).toBeInTheDocument()
  })

  it('should render collapsed sidebar when collapsed prop is true', () => {
    render(<Sidebar collapsed />)
    
    // In collapsed state, the wordmark should be hidden
    expect(screen.queryByText('finna')).not.toBeInTheDocument()
    
    // But section headers should still be visible
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Resources')).toBeInTheDocument()
    expect(screen.getByText('Monitoring')).toBeInTheDocument()
  })
})