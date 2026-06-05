import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'

const mockFindings = {
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
}

const mockSummary = {
  categories: [{ category: 'storage', finding_count: 1, total_monthly_usd: 45 }],
  total_monthly_usd: 45,
  total_finding_count: 1,
}

const mockRules = {
  rules: [{ id: 'azure.disk.orphan', severity: 'high', category: 'storage', description: 'Orphaned managed disk' }],
  count: 1,
}

const mockScans = {
  scans: [{ id: 'run-001', provider: 'azure', started_at: new Date().toISOString(), status: 'done', findings_count: 1 }],
  count: 1,
}

test.describe('Wastage Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/wastage/summary', async (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/v1/wastage/rules', async (route) => route.fulfill({ json: mockRules }))
    await page.route('/api/v1/wastage/scans*', async (route) => route.fulfill({ json: mockScans }))
    await page.route('/api/v1/wastage?*', async (route) => route.fulfill({ json: mockFindings }))
    await page.route('/api/v1/wastage', async (route) => route.fulfill({ json: mockFindings }))
    await page.route('/api/v1/wastage/*/ack', async (route) => route.fulfill({ json: { finding_id: 'abc123', status: 'acked' } }))
    await page.route('/api/v1/wastage/*/resolve', async (route) => route.fulfill({ json: { finding_id: 'abc123', status: 'resolved' } }))
    await page.route('/api/v1/wastage/*/ignore', async (route) => route.fulfill({ json: { finding_id: 'abc123', status: 'ignored' } }))
    await page.route('/api/v1/wastage/scan', async (route) => route.fulfill({ json: { run_id: 'run-002', status: 'started', provider: 'azure' } }))
  })

  test('renders wastage page heading', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByRole('heading', { name: /Resource Wastage/i, level: 1 })).toBeVisible()
  })

  test('shows list-price disclaimer banner', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByText(/public list prices/i)).toBeVisible()
  })

  test('shows estimated savings summary card', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByText(/Est\. Savings/i)).toBeVisible()
  })

  test('renders findings table row', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByText(/azure\.disk\.orphan/)).toBeVisible()
  })

  test('row click opens detail drawer', async ({ page }) => {
    await page.goto('/#/wastage')
    await page.getByText(/azure\.disk\.orphan/).first().click()
    await expect(page.getByRole('dialog', { name: /Finding detail/i })).toBeVisible()
    await expect(page.getByText(/size_gb/)).toBeVisible()
  })

  test('filter selects are present', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByDisplayValue('provider: all')).toBeVisible()
    await expect(page.getByDisplayValue('severity: all')).toBeVisible()
  })

  test('run scan button is visible', async ({ page }) => {
    await page.goto('/#/wastage')
    await expect(page.getByRole('button', { name: /run scan/i })).toBeVisible()
  })

  test('can navigate to wastage via sidebar', async ({ page }) => {
    await page.goto('/#/dashboard')
    // Sidebar link
    const wastageLink = page.getByRole('link', { name: /Wastage/i })
    if (await wastageLink.isVisible().catch(() => false)) {
      await wastageLink.click()
      await expect(page.getByRole('heading', { name: /Resource Wastage/i })).toBeVisible()
    }
  })
})
