import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WastagePage } from './WastagePage'

// Mock all hooks so the component renders without real network calls
jest.mock('@/api/hooks/useWastage', () => ({
  useWastageFindings: jest.fn(() => ({
    data: {
      data: [
        {
          finding_id: 'abc123',
          provider: 'azure',
          account_id: 'sub-001',
          resource_group: 'rg-prod',
          region: 'westeurope',
          resource_id: '/subscriptions/sub-001/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/disk-orphan',
          resource_type: 'Microsoft.Compute/disks',
          rule_id: 'azure.disk.orphan',
          severity: 'high',
          category: 'storage',
          estimated_monthly_usd: 45.0,
          currency: 'USD',
          evidence: { size_gb: 128, sku: 'Premium_LRS' },
          first_seen_at: new Date(Date.now() - 86_400_000 * 3).toISOString(),
          last_seen_at: new Date().toISOString(),
          status: 'open',
          tags: {},
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      has_next: false,
      has_prev: false,
    },
    isLoading: false,
  })),
  useWastageSummary: jest.fn(() => ({
    data: {
      categories: [{ category: 'storage', finding_count: 1, total_monthly_usd: 45 }],
      total_monthly_usd: 45,
      total_finding_count: 1,
    },
  })),
  useWastageRules: jest.fn(() => ({
    data: {
      rules: [{ id: 'azure.disk.orphan', severity: 'high', category: 'storage', description: 'Orphaned disk' }],
      count: 1,
    },
  })),
  useAckFinding: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useResolveFinding: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useIgnoreFinding: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
  useTriggerScan: jest.fn(() => ({ mutate: jest.fn(), isPending: false })),
}))

jest.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: jest.fn(),
    showError: jest.fn(),
  }),
}))

describe('WastagePage', () => {
  it('renders the page heading', () => {
    render(<WastagePage />)
    expect(screen.getByRole('heading', { name: /Resource Wastage/i, level: 1 })).toBeInTheDocument()
  })

  it('shows the list-price disclaimer banner', () => {
    render(<WastagePage />)
    expect(screen.getByRole('note')).toBeInTheDocument()
    expect(screen.getByText(/public list prices/i)).toBeInTheDocument()
  })

  it('displays summary card with estimated savings', () => {
    render(<WastagePage />)
    expect(screen.getByText(/Est\. Savings/i)).toBeInTheDocument()
  })

  it('renders the findings table with one row', () => {
    render(<WastagePage />)
    expect(screen.getByText(/azure\.disk\.orphan/i)).toBeInTheDocument()
  })

  it('shows severity label in table', () => {
    render(<WastagePage />)
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('shows estimated cost in table', () => {
    render(<WastagePage />)
    expect(screen.getByText(/45\.00/)).toBeInTheDocument()
  })

  it('opens detail drawer when row is clicked', async () => {
    render(<WastagePage />)
    const row = screen.getByText(/azure\.disk\.orphan/)
    await userEvent.click(row)
    expect(screen.getByRole('dialog', { name: /Finding detail/i })).toBeInTheDocument()
  })

  it('closes drawer when close button is clicked', async () => {
    render(<WastagePage />)
    await userEvent.click(screen.getByText(/azure\.disk\.orphan/))
    const closeBtn = screen.getByRole('button', { name: /✕/i })
    await userEvent.click(closeBtn)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows filter selects', () => {
    render(<WastagePage />)
    expect(screen.getByDisplayValue('provider: all')).toBeInTheDocument()
    expect(screen.getByDisplayValue('severity: all')).toBeInTheDocument()
    expect(screen.getByDisplayValue('status: all')).toBeInTheDocument()
  })

  it('shows run scan button', () => {
    render(<WastagePage />)
    expect(screen.getByRole('button', { name: /run scan/i })).toBeInTheDocument()
  })
})
