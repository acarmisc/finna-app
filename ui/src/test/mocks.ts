/**
 * Mock for localStorage to use in tests
 */
export const createMockStorage = (): Storage => {
  let store: Record<string, string> = {}

  return {
    get length() {
      return Object.keys(store).length
    },
    clear() {
      store = {}
    },
    getItem(key: string) {
      return store[key] ?? null
    },
    key(index: number) {
      const keys = Object.keys(store)
      return keys[index] ?? null
    },
    removeItem(key: string) {
      delete store[key]
    },
    setItem(key: string, value: string) {
      store[key] = value
    },
  }
}

/**
 * Mock for the auth store
 */
export const mockAuthStore = {
  token: 'test-token-12345',
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  setToken: jest.fn(),
  checkAuth: jest.fn(),
}
