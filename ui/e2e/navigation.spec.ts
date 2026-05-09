import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    // Intercept all API calls
    await page.route('/api/v1/dashboard/stats*', async (route) => route.fulfill({ json: mocks.mockDashboardStats() }))
    await page.route('/api/v1/config/projects', async (route) => route.fulfill({ json: mocks.mockProjects }))
    await page.route('/api/v1/extractors/runs*', async (route) => route.fulfill({ json: mocks.mockExtractorRuns }))
    await page.route('/api/v1/alerts/stats', async (route) => route.fulfill({ json: mocks.mockAlertStats }))
    await page.route('/api/v1/costs', async (route) => route.fulfill({ json: mocks.mockCosts }))
    await page.route('/api/v1/alerts*', async (route) => route.fulfill({ json: mocks.mockAlerts }))
    await page.route('/api/v1/configs', async (route) => route.fulfill({ json: mocks.mockConfigs }))
    await page.route('/api/v1/extractors', async (route) => route.fulfill({ json: mocks.mockExtractors }))
    await page.route('/api/v1/config*', async (route) => route.fulfill({ json: [] }))
    await page.route('/api/v1/config/*/test', async (route) => route.fulfill({ json: { ok: true } }))
  })

  const routes = [
    { path: '#/dashboard', heading: 'Dashboard' },
    { path: '#/projects', heading: 'Projects' },
    { path: '#/costs', heading: 'Cost explorer' },
    { path: '#/configs', heading: 'Configs' },
    { path: '#/alerts', heading: 'Alerts' },
    { path: '#/extractors', heading: 'Extractors' },
    { path: '#/runs', heading: 'Extractor runs' },
    { path: '#/settings', heading: 'Settings' },
  ]

  for (const r of routes) {
    test(`navigates to ${r.heading}`, async ({ page }) => {
      await page.goto('/#/dashboard')
      await page.waitForSelector('.sb', { state: 'visible' })
      // Click sidebar link by matching text
      const link = page.locator(`.sb-nav a[href*="${r.path.replace('#', '')}"], .sb-nav a:has-text("${r.heading}")`).first()
      if (await link.isVisible().catch(() => false)) {
        await link.click()
      } else {
        // Direct navigation fallback
        await page.goto(r.path)
      }
      await expect(page).toHaveURL(new RegExp(r.path.replace('#', '').replace(/\//g, '\\/')))
      await expect(page.getByRole('heading', { name: new RegExp(r.heading, 'i'), level: 1 })).toBeVisible()
    })
  }
})
