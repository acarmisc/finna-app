import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './SettingsPage'
import { useTheme } from '@/contexts/ThemeContext'
import { useToast } from '@/contexts/ToastContext'

// Mock contexts
jest.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: jest.fn(),
    toggleTheme: jest.fn()
  })
}))

jest.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: jest.fn(),
    showSuccess: jest.fn(),
    showError: jest.fn()
  })
}))

describe('SettingsPage Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render settings page header', () => {
    render(<SettingsPage />)
    
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('// user preferences · POST /api/v1/auth/profile')).toBeInTheDocument()
  })

  it('should render navigation sections', () => {
    render(<SettingsPage />)
    
    const sectionButtons = screen.getAllByRole('button')
    console.log('Number of buttons:', sectionButtons.length)
    sectionButtons.forEach((button, index) => {
      console.log(`Button ${index}: "${button.textContent}"`)
    })
    
    // We have 7 buttons because there's also a save button
    expect(sectionButtons.length).toBeGreaterThanOrEqual(5) // At least the 5 section buttons
    
    // Check that we have the expected section buttons
    const buttonTexts = sectionButtons.map(b => b.textContent.trim())
    expect(buttonTexts).toContain('// profile')
    expect(buttonTexts).toContain('// organization')
    expect(buttonTexts).toContain('// api keys')
    expect(buttonTexts).toContain('// notifications')
    expect(buttonTexts).toContain('// preferences')
  })
})