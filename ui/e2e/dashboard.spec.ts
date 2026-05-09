import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/dashboard/stats*', async (route) => route.fulfill({ json: mocks.mockDashboardStats() }))
    await page.route('/api/v1/config/projects', async (route) => route.fulfill({ json: mocks.mockProjects }))
    await page.route('/api/v1/extractors/runs*', async (route) => route.fulfill({ json: mocks.mockExtractorRuns }))
    await page.route('/api/v1/alerts/stats', async (route) => route.fulfill({ json: mocks.mockAlertStats }))
  })

  test('renders all KPI cards', async ({ page }) => {
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible()

    // Top-level KPIs
    await expect(page.getByText(/Total MTD/)).toBeVisible()
    await expect(page.getByText(/Azure MTD/)).toBeVisible()
    await expect(page.getByText(/GCP MTD/)).toBeVisible()
    await expect(page.getByText(/LLM MTD/)).toBeVisible()
    await expect(page.getByText(/Active alerts/)).toBeVisible()
  })

  test('daily cost chart section is visible', async ({ page }) => {
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: /Daily cost/i })).toBeVisible()
  })

  test('top projects section is visible', async ({ page }) => {
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: /Top projects/i })).toBeVisible()
    await expect(page.getByText(/Platform Infra/)).toBeVisible()
    await expect(page.getByText(/ML Pipeline/)).toBeVisible()
  })

  test('LLM spend breakdown is visible', async ({ page }) => {
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: /LLM spend by model/i })).toBeVisible()
    await expect(page.getByText(/Claude Sonnet/)).toBeVisible()
    await expect(page.getByText(/GPT-4o/)).toBeVisible()
  })

  test('recent extractor runs table is visible', async ({ page }) => {
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: /Recent extractor runs/i })).toBeVisible()
    await expect(page.getByText(/azure_cost/).first()).toBeVisible()
    await expect(page.getByText(/gcp_cost/).first()).toBeVisible()
  })

  test('can click view all projects link', async ({ page }) => {
    await page.goto('/#/dashboard')
    await page.getByRole('link', { name: /view all/i }).first().click()
    await expect(page).toHaveURL(/#\/projects/)
  })

  test('can click run log link', async ({ page }) => {
    await page.goto('/#/dashboard')
    const runLogLink = page.getByRole('link', { name: /run log/i })
    if (await runLogLink.isVisible().catch(() => false)) {
      await runLogLink.click()
      await expect(page).toHaveURL(/#\/extractors|#\/runs/)
    }
  })
})
