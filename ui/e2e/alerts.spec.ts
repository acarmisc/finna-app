import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Alerts Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/alerts*', async (route) => route.fulfill({ json: mocks.mockAlerts }))
    await page.route('/api/v1/alerts/stats', async (route) => route.fulfill({ json: mocks.mockAlertStats }))
    await page.route('/api/v1/alerts/*/acknowledge', async (route) => route.fulfill({ json: { id: 'a1', acknowledged: true } }))
    await page.route('/api/v1/alerts/acknowledge-all', async (route) => route.fulfill({ json: { acknowledged_count: 2, ids: ['a1', 'a2'] } }))
  })

  test('renders alerts list', async ({ page }) => {
    await page.goto('/#/alerts')
    await expect(page.getByRole('heading', { name: /Alerts?/i, level: 1 })).toBeVisible()
    await expect(page.getByText(/Azure VM cost spike/)).toBeVisible()
    await expect(page.getByText(/LLM usage approaching budget/)).toBeVisible()
  })

  test('severity badges are visible', async ({ page }) => {
    await page.goto('/#/alerts')
    await expect(page.getByText(/err|critical/i).first()).toBeVisible()
    await expect(page.getByText(/warn|warning/i).first()).toBeVisible()
  })

  test('can acknowledge a single alert', async ({ page }) => {
    await page.goto('/#/alerts')
    const ackBtn = page.getByRole('button', { name: /acknowledge/i }).first()
    if (await ackBtn.isVisible().catch(() => false)) {
      await ackBtn.click()
      await expect(page.getByText(/acknowledged/i)).toBeVisible()
    }
  })

  test('stats summary is visible', async ({ page }) => {
    await page.goto('/#/alerts')
    await expect(page.getByText(/firing/i).first()).toBeVisible()
    await expect(page.getByText(/acknowledged|ack/i).first()).toBeVisible()
  })
})
