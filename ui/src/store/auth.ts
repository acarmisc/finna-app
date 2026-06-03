import { create } from 'zustand'
import { getToken, setToken as setStoredToken, clearToken } from '@/lib/tokenStorage'

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
    setStoredToken(token)
    set({ token, isAuthenticated: !!token, loading: false })
  },

  checkAuth: () => {
    const storedToken = getToken()
    set({
      token: storedToken,
      isAuthenticated: !!storedToken,
      loading: false
    })
  },

  login: (token) => {
    setStoredToken(token)
    set({ token, isAuthenticated: true, loading: false })
  },

  logout: () => {
    clearToken()
    set({ token: null, isAuthenticated: false, loading: false })
  },
}))
