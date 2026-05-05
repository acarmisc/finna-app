const { useAuthStore } = require('./auth')

describe('Auth Store', () => {
  beforeEach(() => {
    localStorage.removeItem('finna_token')
    sessionStorage.removeItem('finna_token')
    useAuthStore.getState().logout()
  })

  it('should initialize with correct default state', () => {
    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    // Note: Initial loading state is true but gets set to false by checkAuth during initialization
    // In practice, we check the actions rather than the initial loading state
  })

  it('should set token and update auth state', () => {
    const { setToken } = useAuthStore.getState()
    setToken('test-token-123')
    const state = useAuthStore.getState()
    expect(state.token).toBe('test-token-123')
    expect(state.isAuthenticated).toBe(true)
    expect(state.loading).toBe(false)
  })

  it('should remove token when setting null', () => {
    const { setToken } = useAuthStore.getState()
    setToken('test-token-123')
    setToken(null)
    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('should handle login action', () => {
    const { login } = useAuthStore.getState()
    login('test-jwt-token')
    const state = useAuthStore.getState()
    expect(state.token).toBe('test-jwt-token')
    expect(state.isAuthenticated).toBe(true)
  })

  it('should handle logout action', () => {
    const { setToken } = useAuthStore.getState()
    setToken('test-token-123')
    const { logout } = useAuthStore.getState()
    logout()
    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(localStorage.getItem('finna_token')).toBeNull()
    expect(sessionStorage.getItem('finna_token')).toBeNull()
  })

  it('should check auth from localStorage', () => {
    localStorage.setItem('finna_token', 'stored-token')
    const { checkAuth } = useAuthStore.getState()
    checkAuth()
    const state = useAuthStore.getState()
    expect(state.token).toBe('stored-token')
    expect(state.isAuthenticated).toBe(true)
  })

  it('should clear localStorage on logout', () => {
    localStorage.setItem('finna_token', 'token-to-clear')
    sessionStorage.setItem('finna_token', 'token-to-clear')
    const { logout } = useAuthStore.getState()
    logout()
    expect(localStorage.getItem('finna_token')).toBeNull()
    expect(sessionStorage.getItem('finna_token')).toBeNull()
  })

  it('should persist token in localStorage when set', () => {
    const { setToken } = useAuthStore.getState()
    setToken('persistent-token')
    
    expect(localStorage.getItem('finna_token')).toBe('persistent-token')
    expect(sessionStorage.getItem('finna_token')).toBe('persistent-token')
  })

  it('should handle multiple login/logout cycles', () => {
    const { login, logout } = useAuthStore.getState()
    
    // First login
    login('token1')
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    
    // Logout
    logout()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    
    // Second login
    login('token2')
    expect(useAuthStore.getState().token).toBe('token2')
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    
    // Second logout
    logout()
    expect(localStorage.getItem('finna_token')).toBeNull()
    expect(sessionStorage.getItem('finna_token')).toBeNull()
  })
})