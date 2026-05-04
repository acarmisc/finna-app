import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Sidebar from './Sidebar'
import { MemoryRouter } from 'react-router-dom'

describe('Sidebar Component', () => {
  const user = userEvent.setup()

  it('should render logo with toggle functionality', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar collapsed={false} onToggle={() => {}} />
      </MemoryRouter>
    )

    // Check for caret element
    expect(screen.getByText('›')).toBeInTheDocument()
    
    // Check for wordmark when not collapsed
    expect(screen.getByText('finna')).toBeInTheDocument()
  })

  it('should render navigation items correctly', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar collapsed={false} onToggle={() => {}} />
      </MemoryRouter>
    )

    // Check section headers
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Resources')).toBeInTheDocument()
    expect(screen.getByText('Monitoring')).toBeInTheDocument()

    // Check navigation items
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /cost explorer/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /projects/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /cloud configs/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /extractors/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /alerts/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument()
  })

  it('should highlight active navigation item', () => {
    render(
      <MemoryRouter initialEntries={['/costs']}>
        <Sidebar collapsed={false} onToggle={() => {}} activeBase="/costs" />
      </MemoryRouter>
    )

    // Check that costs link is active - get all links and find the active one
    const allLinks = screen.getAllByRole('link')
    const costsLink = allLinks.find(link => 
      link.textContent?.includes('Cost explorer') && 
      link.classList.contains('active')
    )
    expect(costsLink).toBeInTheDocument()
  })

  it('should render alert count badge when count > 0', () => {
    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Sidebar collapsed={false} onToggle={() => {}} counts={{ alerts: 5 }} />
      </MemoryRouter>
    )

    // Check that alert badge is rendered with correct count
    const alertLinks = screen.getAllByRole('link', { name: /alerts/i })
    expect(alertLinks.length).toBeGreaterThan(0)
    
    // Find the link that contains the count
    const alertLinkWithCount = alertLinks.find(link => 
      link.querySelector('.count')?.textContent?.trim() === '5'
    )
    expect(alertLinkWithCount).toBeInTheDocument()
  })

  it('should not render alert count badge when count is 0', () => {
    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Sidebar collapsed={false} onToggle={() => {}} counts={{ alerts: 0 }} />
      </MemoryRouter>
    )

    // Check that alert badge is not rendered when count is 0
    const alertLinks = screen.getAllByRole('link', { name: /alerts/i })
    expect(alertLinks.length).toBeGreaterThan(0)
    
    // Verify none of the alert links have a count badge with 0
    const alertLinksWithZeroCount = alertLinks.filter(link => 
      link.querySelector('.count')?.textContent?.trim() === '0'
    )
    expect(alertLinksWithZeroCount.length).toBe(0)
  })

  it('should render user information correctly', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar collapsed={false} onToggle={() => {}} onLogout={() => {}} />
      </MemoryRouter>
    )

    // Check user info
    expect(screen.getByText(/finops@acme\.co/i)).toBeInTheDocument()
    expect(screen.getByText(/API · healthy/i)).toBeInTheDocument()
    
    // Check health indicator
    expect(screen.getByTitle(/API healthy/i)).toBeInTheDocument()
  })

  it('should have proper accessibility attributes on main elements', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar collapsed={false} onToggle={() => {}} onLogout={() => {}} />
      </MemoryRouter>
    )

    // Check sidebar has aria-label
    const sidebar = screen.getByRole('complementary', { name: /main navigation/i })
    expect(sidebar).toBeInTheDocument()
    
    // Check nav has aria-label
    const nav = screen.getByRole('navigation', { name: /primary navigation/i })
    expect(nav).toBeInTheDocument()
    
    // Check sections have proper roles
    const overviewSection = screen.getByRole('separator', { name: /overview/i })
    expect(overviewSection).toBeInTheDocument()
  })
})