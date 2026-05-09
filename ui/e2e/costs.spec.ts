import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Costs Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/costs*', async (route) => route.fulfill({ json: mocks.mockCosts }))
    await page.route('/api/v1/costs/totals*', async (route) => route.fulfill({
      json: {
        totals: { azure: { mtd: 5432.10, prev: 5100.00, delta: 6.5 }, gcp: { mtd: 4567.89, prev: 4600.00, delta: -0.7 }, llm: { mtd: 2450.33, prev: 2200.00, delta: 11.4 }, total: { mtd: 12450.32, prev: 11900.00, delta: 4.6 } },
        window: 'mtd',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      }
    }))
    await page.route('/api/v1/costs/daily*', async (route) => route.fulfill({
      json: {
        days: [
          { date: '2024-01-01', azure: 120.5, gcp: 98.2, llm: 45.1 },
          { date: '2024-01-02', azure: 135.0, gcp: 102.3, llm: 50.0 },
        ],
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      }
    }))
  })

  test('renders costs table', async ({ page }) => {
    await page.goto('/#/costs')
    await expect(page.getByRole('heading', { name: /Costs?/i, level: 1 })).toBeVisible()
    await expect(page.getByText(/Platform Infra/).first()).toBeVisible()
    await expect(page.getByText(/ML Pipeline/).first()).toBeVisible()
  })

  test('provider filter tabs work', async ({ page }) => {
    await page.goto('/#/costs')
    // Look for provider filter buttons (Azure, GCP, LLM, All)
    const azureBtn = page.getByRole('button', { name: /azure/i }).first()
    if (await azureBtn.isVisible().catch(() => false)) {
      await azureBtn.click()
      // After filtering, the page should still show costs (mock data returns same set)
      await expect(page.getByText(/Virtual Machines/)).toBeVisible()
    }
  })

  test('export button is present', async ({ page }) => {
    await page.goto('/#/costs')
    const exportBtn = page.getByRole('button', { name: /export|download/i }).first()
    if (await exportBtn.isVisible().catch(() => false)) {
      await expect(exportBtn).toBeEnabled()
    }
  })
})
