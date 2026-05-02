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
      localStorage.setItem('finna_token', token)
    } else {
      localStorage.removeItem('finna_token')
    }
    set({ token, isAuthenticated: !!token, loading: false })
  },

  checkAuth: () => {
    const storedToken = localStorage.getItem('finna_token')
    set({ 
      token: storedToken, 
      isAuthenticated: !!storedToken, 
      loading: false 
    })
  },

  login: (token) => {
    set({ token, isAuthenticated: true, loading: false })
  },

  logout: () => {
    set({ token: null, isAuthenticated: false, loading: false })
    localStorage.removeItem('finna_token')
  },
}))
