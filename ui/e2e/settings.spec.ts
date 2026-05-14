import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
  })

  test('renders settings screen', async ({ page }) => {
    await page.goto('/#/settings')
    await expect(page.getByRole('heading', { name: /Settings?/i, level: 1 })).toBeVisible()
    await expect(page.getByText('// account, orchestrator, integrations')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Account/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Orchestrator/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Danger zone/i })).toBeVisible()
  })
})
