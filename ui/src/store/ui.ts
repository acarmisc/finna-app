import { create } from 'zustand'

export interface ViewState {
  sidebarCollapsed: boolean
  theme: 'dark' | 'light'
  dateRange: {
    start: Date | null
    end: Date | null
  }
}

export interface ViewActions {
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleTheme: () => void
  setTheme: (theme: 'dark' | 'light') => void
  setDateRange: (start: Date | null, end: Date | null) => void
  resetDateRange: () => void
}

export const useViewStore = create<ViewState & ViewActions>()((set) => ({
  sidebarCollapsed: false,
  theme: 'dark',
  dateRange: {
    start: null,
    end: null,
  },

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarCollapsed: (collapsed) =>
    set({ sidebarCollapsed: collapsed }),

  toggleTheme: () =>
    set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),

  setTheme: (theme) =>
    set({ theme }),

  setDateRange: (start, end) =>
    set({ dateRange: { start, end } }),

  resetDateRange: () =>
    set({ dateRange: { start: null, end: null } }),
}))
