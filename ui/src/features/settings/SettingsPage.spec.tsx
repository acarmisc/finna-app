import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './SettingsPage'

describe('SettingsPage Component', () => {
  it('should render settings page header', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('// account, orchestrator, integrations')).toBeInTheDocument()
  })

  it('should render Account card with fields and save button', () => {
    render(<SettingsPage />)
    expect(screen.getByRole('heading', { name: /Account/i })).toBeInTheDocument()
    expect(screen.getByDisplayValue('finops@acme.co')).toBeInTheDocument()
    expect(screen.getByDisplayValue('acme')).toBeDisabled()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
  })

  it('should render Orchestrator card with endpoint and scheduler', () => {
    render(<SettingsPage />)
    expect(screen.getByRole('heading', { name: /Orchestrator/i })).toBeInTheDocument()
    expect(screen.getByText(/api endpoint/i)).toBeInTheDocument()
    expect(screen.getByText(/healthy/i)).toBeInTheDocument()
    expect(screen.getByText(/scheduler/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /edit schedule/i })).toBeInTheDocument()
  })

  it('should render Danger zone card with purge button', async () => {
    render(<SettingsPage />)
    expect(screen.getByRole('heading', { name: /Danger zone/i })).toBeInTheDocument()

    const cardBd = screen.getByRole('heading', { name: /Danger zone/i }).closest('.card')?.querySelector('.card-bd')
    expect(cardBd).toBeTruthy()
    expect(cardBd!.textContent).toMatch(/Purge cost records/)

    const purgeBtn = screen.getByRole('button', { name: /purge/i })
    expect(purgeBtn).toBeInTheDocument()

    await userEvent.click(purgeBtn)
    expect(screen.getByText(/permanently delete/i)).toBeInTheDocument()
  })
})
