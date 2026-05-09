import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Projects', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('/api/v1/config/projects', async (route) => route.fulfill({ json: mocks.mockProjects }))
    await page.route('/api/v1/dashboard/stats*', async (route) => route.fulfill({ json: mocks.mockDashboardStats() }))
    await page.route('/api/v1/alerts/stats', async (route) => route.fulfill({ json: mocks.mockAlertStats }))
    await page.route('/api/v1/extractors/runs*', async (route) => route.fulfill({ json: mocks.mockExtractorRuns }))
    await page.route('/api/v1/costs', async (route) => route.fulfill({ json: mocks.mockCosts }))
    // Detail page routes
    await page.route('/api/v1/config/projects/*', async (route) => {
      const slug = route.request().url().split('/').pop()
      const proj = mocks.mockProjects.find(p => p.slug === slug)
      if (proj) await route.fulfill({ json: proj })
      else await route.fulfill({ status: 404, json: { detail: 'Not found' } })
    })
    await page.route('/api/v1/config/projects', async (route, request) => {
      if (request.method() === 'POST') {
        const body = await request.postDataJSON()
        await route.fulfill({ status: 201, json: { id: 'new-p', ...body, slug: body.slug || body.name?.toLowerCase().replace(/\s+/g, '-'), mtd: 0.0, created: new Date().toISOString() } })
      } else {
        await route.fulfill({ json: mocks.mockProjects })
      }
    })
  })

  test('projects list renders', async ({ page }) => {
    await page.goto('/#/projects')
    await expect(page.getByRole('heading', { name: 'Projects', level: 1 })).toBeVisible()
    await expect(page.getByText(/Platform Infra/)).toBeVisible()
    await expect(page.getByText(/ML Pipeline/)).toBeVisible()
  })

  test('can navigate to project detail', async ({ page }) => {
    await page.goto('/#/projects')
    await page.getByText(/Platform Infra/).first().click()
    await expect(page).toHaveURL(/#\/projects\/platform-infra/)
    await expect(page.getByRole('heading', { name: /Platform Infra/, level: 1 })).toBeVisible()
  })

  test('can create a new project', async ({ page }) => {
    await page.goto('/#/projects/new')
    await expect(page).toHaveURL(/#\/projects\/new/)

    // Step 1: configs (optional) - click next step
    await page.getByRole('button', { name: /next step →/i }).click()

    // Step 2: details - fill required fields
    await page.locator('input[placeholder="prod-platform"]').first().fill('Test Project')
    await page.locator('input[placeholder="platform-eng"]').fill('test-team')
    await page.locator('input[placeholder="CC-1001"]').fill('TC-001')
    await page.locator('input[placeholder="14000"]').fill('5000')
    await page.getByRole('button', { name: /next step →/i }).click()

    // Step 3: review - click create project
    await page.getByRole('button', { name: /create project/i }).click()

    // Should redirect to projects list
    await expect(page).toHaveURL(/#\/projects/)
  })
})
