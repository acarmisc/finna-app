import { create } from 'zustand'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  loading: boolean
}

interface AuthActions {
  setToken: (token: string | null) => void
  login: (token: string) => void
  logout: () => void
  checkAuth: () => void
}

const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem('finna_token') || localStorage.getItem('finna_token')
}

export const useAuthStore = create<AuthState & AuthActions>()((set, get) => ({
  token: null,
  isAuthenticated: false,
  loading: true,

  setToken: (token) => {
    if (token) {
      sessionStorage.setItem('finna_token', token)
      // Keep localStorage for session restoration fallback
      localStorage.setItem('finna_token', token)
    } else {
      sessionStorage.removeItem('finna_token')
      localStorage.removeItem('finna_token')
    }
    set({ token, isAuthenticated: !!token, loading: false })
  },

  checkAuth: () => {
    // Prefer sessionStorage, fall back to localStorage for session restoration
    const storedToken = getStoredToken()
    set({ 
      token: storedToken, 
      isAuthenticated: !!storedToken, 
      loading: false 
    })
  },

  login: (token) => {
    // Store in both sessionStorage (primary) and localStorage (fallback)
    sessionStorage.setItem('finna_token', token)
    localStorage.setItem('finna_token', token)
    set({ token, isAuthenticated: true, loading: false })
  },

  logout: () => {
    // Clear both storage types
    sessionStorage.removeItem('finna_token')
    localStorage.removeItem('finna_token')
    set({ token: null, isAuthenticated: false, loading: false })
  },
}))

/**
 * Get the current auth token.
 * This is the centralized helper for accessing auth tokens.
 * Uses sessionStorage (primary) with localStorage fallback for session restoration.
 * Falls back to direct storage lookup if useAuthStore is not yet initialized.
 */
export function getAuthToken(): string | null {
  // Try Zustand store first (most current)
  const storeToken = useAuthStore.getState().token
  if (storeToken) return storeToken
  
  // Fallback to direct storage lookup
  return getStoredToken()
}
