/**
 * Centralized token storage wrapper for XSS defense-in-depth.
 *
 * TODO(security): migrate to HttpOnly cookie + CSRF token. See SECURITY_AUDIT.md §2.7.
 * This is a transitional layer that centralizes token access, making a future cookie migration
 * easier (single file to change). Full migration requires backend coordination and CSRF handling.
 *
 * Current implementation:
 * - Wraps localStorage.getItem/setItem/removeItem for 'finna_token'
 * - Also manages sessionStorage as primary storage
 * - Token is persisted across page reloads via localStorage fallback
 */

const TOKEN_KEY = 'finna_token'

/**
 * Get the current token from storage.
 * Prefers sessionStorage (session-scoped), falls back to localStorage (persistent).
 */
export function getToken(): string | null {
  // Prefer sessionStorage (session-scoped), fall back to localStorage
  const token = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY)
  return token
}

/**
 * Set the token in storage (both sessionStorage and localStorage).
 * sessionStorage is the primary store; localStorage serves as a fallback for session restoration.
 */
export function setToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    sessionStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_KEY)
  }
}

/**
 * Clear the token from all storage locations.
 */
export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(TOKEN_KEY)
}
