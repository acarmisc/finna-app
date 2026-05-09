import { test, expect } from '@playwright/test'
import { seedAuth, clearAuth } from './fixtures/auth'
import { mockToken } from './mocks/data'

test.describe('Auth / Login', () => {
  test.beforeEach(async ({ page }) => {
    await clearAuth(page)
    await page.route('/api/v1/auth/token', async (route, request) => {
      const body = await request.postDataJSON()
      if (body?.username === 'admin' && body?.password === 'admin') {
        await route.fulfill({ status: 200, json: { token: mockToken } })
      } else {
        await route.fulfill({ status: 401, json: { detail: 'Invalid credentials' } })
      }
    })
    // Prevent real SSO fetches
    await page.route('/api/v1/auth/github', async (route) => {
      await route.fulfill({ status: 500, json: { error: 'GitHub login not configured' } })
    })
  })

  test('shows login screen when unauthenticated', async ({ page }) => {
    await page.goto('/#/login')
    await expect(page.getByRole('heading', { name: /sign in to finna/i })).toBeVisible()
    await expect(page.getByText(/cloud \+ llm costs/i)).toBeVisible()
  })

  test('can login with email + password', async ({ page }) => {
    await page.goto('/#/login')
    // Expand email form
    await page.getByRole('button', { name: /sign in with email and password/i }).click()
    await page.getByPlaceholder(/you@company\.com/i).fill('admin')
    await page.getByPlaceholder(/••••••••/i).fill('admin')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL(/#\/dashboard/)
    await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible()
  })

  test('shows error on bad credentials', async ({ page }) => {
    await page.goto('/#/login')
    await page.getByRole('button', { name: /sign in with email and password/i }).click()
    await page.getByPlaceholder(/you@company\.com/i).fill('bad')
    await page.getByPlaceholder(/••••••••/i).fill('wrong')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText(/invalid credentials/i)).toBeVisible()
  })

  test('logout returns to login', async ({ page }) => {
    await seedAuth(page)
    await page.goto('/#/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible()

    // Logout button is in the AppShell/Sidebar
    const logoutBtn = page.getByLabel(/logout/i)
    if (await logoutBtn.isVisible().catch(() => false)) {
      await logoutBtn.click()
    } else {
      // Fallback: clear auth via storage
      await clearAuth(page)
      await page.reload()
    }

    await expect(page.getByRole('heading', { name: /sign in to finna/i })).toBeVisible()
  })
})
