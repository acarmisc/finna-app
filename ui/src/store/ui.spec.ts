const { useViewStore } = require('./ui')

describe('View Store', () => {
  beforeEach(() => {
    useViewStore.getState().resetDateRange()
  })

  it('should initialize with correct default state', () => {
    const state = useViewStore.getState()
    expect(state.theme).toBe('dark')
    expect(state.sidebarCollapsed).toBe(false)
  })

  it('should toggle sidebar', () => {
    const { toggleSidebar } = useViewStore.getState()
    expect(useViewStore.getState().sidebarCollapsed).toBe(false)
    toggleSidebar()
    expect(useViewStore.getState().sidebarCollapsed).toBe(true)
    toggleSidebar()
    expect(useViewStore.getState().sidebarCollapsed).toBe(false)
  })

  it('should toggle theme', () => {
    const { toggleTheme } = useViewStore.getState()
    expect(useViewStore.getState().theme).toBe('dark')
    toggleTheme()
    expect(useViewStore.getState().theme).toBe('light')
    toggleTheme()
    expect(useViewStore.getState().theme).toBe('dark')
  })

  it('should reset dateRange only', () => {
    const { setDateRange, resetDateRange } = useViewStore.getState()
    setDateRange(new Date('2024-01-01'), new Date('2024-12-31'))
    expect(useViewStore.getState().dateRange.start).not.toBeNull()
    
    resetDateRange()
    expect(useViewStore.getState().dateRange.start).toBeNull()
    expect(useViewStore.getState().dateRange.end).toBeNull()
  })
})
