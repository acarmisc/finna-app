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
    const storedToken = sessionStorage.getItem('finna_token') || localStorage.getItem('finna_token')
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

// Centralized helper to get auth token - use this instead of localStorage.getItem('finna_token')
export const getAuthToken = (): string | null => {
  return useAuthStore.getState().token
}

// Allow localStorage access in this file only
// eslint-disable-next-line no-restricted-globals
const _localStorage = localStorage
