import type { Page } from '@playwright/test'
import { mockToken } from '../mocks/data'

/**
 * Seed auth state directly into storage (sessionStorage + localStorage)
 * so the app sees an authenticated user without hitting the backend.
 * Navigates to the app root first, injects the token, then reloads
 * so React picks it up on mount.
 */
export async function seedAuth(page: Page) {
  await page.goto('/')
  await page.evaluate((token) => {
    sessionStorage.setItem('finna_token', token)
    localStorage.setItem('finna_token', token)
  }, mockToken)
  await page.reload()
}

/**
 * Log out by clearing both storage keys and reloading.
 */
export async function clearAuth(page: Page) {
  await page.goto('/')
  await page.evaluate(() => {
    sessionStorage.removeItem('finna_token')
    localStorage.removeItem('finna_token')
  })
  await page.reload()
}
