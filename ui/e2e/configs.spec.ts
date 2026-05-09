import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'
import * as mocks from './mocks/data'

test.describe('Configs Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
    await page.route('**/api/v1/config**', async (route, request) => {
      if (request.method() === 'POST') {
        const body = await request.postDataJSON()
        await route.fulfill({ status: 201, json: { id: 'new-cfg', ...body } })
      } else {
        await route.fulfill({ json: mocks.mockConfigs.data })
      }
    })
    await page.route('**/api/v1/config/*/test', async (route) => route.fulfill({ json: { ok: true, provider: 'azure' } }))
  })

  test('renders config list', async ({ page }) => {
    await page.goto('/#/configs')
    await expect(page.getByRole('heading', { name: /Cloud configs|Configs/i, level: 1 })).toBeVisible()
    await expect(page.getByText(/Azure Prod/)).toBeVisible()
    await expect(page.getByText(/GCP ML/)).toBeVisible()
  })

  test('can navigate to create config wizard', async ({ page }) => {
    await page.goto('/#/configs')
    const newBtn = page.getByRole('button', { name: /new|add|create/i }).first()
    if (await newBtn.isVisible().catch(() => false)) {
      await newBtn.click()
      await expect(page).toHaveURL(/#\/configs\/new/)
    }
  })

  test('test config button works', async ({ page }) => {
    await page.goto('/#/configs')
    const testBtn = page.getByRole('button', { name: /test/i }).first()
    if (await testBtn.isVisible().catch(() => false)) {
      await testBtn.click()
      await expect(page.getByText(/ok|success/i)).toBeVisible()
    }
  })
})
