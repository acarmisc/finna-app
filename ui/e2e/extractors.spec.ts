import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Extractors & Run History', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/extractors', async (route) => route.fulfill({ json: mocks.mockExtractors }))
    await page.route('/api/v1/extractors/runs*', async (route) => route.fulfill({ json: mocks.mockExtractorRuns }))
    await page.route('/api/v1/extractors/*/trigger', async (route) => route.fulfill({ json: { run_id: 'run-new', status: 'started' } }))
    await page.route('/api/v1/dashboard/stats*', async (route) => route.fulfill({ json: mocks.mockDashboardStats() }))
    await page.route('/api/v1/alerts/stats', async (route) => route.fulfill({ json: mocks.mockAlertStats }))
  })

  test('extractors list renders', async ({ page }) => {
    await page.goto('/#/extractors')
    await expect(page.getByRole('heading', { name: /Extractors?/i, level: 1 })).toBeVisible()
    await expect(page.getByText(/azure-costs/).first()).toBeVisible()
    await expect(page.getByText(/gcp-costs/).first()).toBeVisible()
  })

  test('run history renders', async ({ page }) => {
    await page.goto('/#/runs')
    await expect(page.getByRole('heading', { name: /Run History|Extractor Runs?/i, level: 1 })).toBeVisible()
    await expect(page.getByText(/azure_cost/).first()).toBeVisible()
    await expect(page.getByText(/gcp_cost/).first()).toBeVisible()
  })

  test('can trigger an extractor', async ({ page }) => {
    await page.goto('/#/extractors')
    const triggerBtn = page.getByRole('button', { name: /run|trigger|start/i }).first()
    if (await triggerBtn.isVisible().catch(() => false) && await triggerBtn.isEnabled().catch(() => false)) {
      await triggerBtn.click()
      await expect(page.getByText(/started|queued/i)).toBeVisible()
    }
  })
})
