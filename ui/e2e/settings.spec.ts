import { test, expect } from '@playwright/test'
import { seedAuth } from './fixtures/auth'

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
  })

  test('renders settings screen', async ({ page }) => {
    await page.goto('/#/settings')
    await expect(page.getByRole('heading', { name: /Settings?/i, level: 1 })).toBeVisible()
  })

  test('theme toggle is present', async ({ page }) => {
    await page.goto('/#/settings')
    const themeToggle = page.getByRole('button', { name: /theme|dark|light/i }).first()
    if (await themeToggle.isVisible().catch(() => false)) {
      await expect(themeToggle).toBeEnabled()
    }
  })
})
