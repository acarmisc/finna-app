import React from 'react'

export const Badge = () => <span data-testid="mock-badge">badge</span>
export const Icon = () => <span data-testid="mock-icon">icon</span>
export const Button = () => <button data-testid="mock-button">Button</button>
export const ProviderBadge = () => <span data-testid="mock-provider-badge">badge</span>
export const StatusBadge = () => <span data-testid="mock-status-badge">status</span>
export const SeverityBadge = () => <span data-testid="mock-severity-badge">severity</span>
export const StatCard = () => <div data-testid="mock-stat-card">StatCard</div>
export const ProgressBar = () => <div data-testid="mock-progress-bar">ProgressBar</div>
export const CostDeltaCell = () => <span data-testid="mock-cost-delta-cell">delta</span>
export const EmptyState = () => <div data-testid="mock-empty-state">Empty</div>
export const Dialog = () => <div data-testid="mock-dialog">Dialog</div>
export const ToastProvider = ({ children }: { children: React.ReactNode }) => <>{children}</>
export const useToast = () => ({ showToast: jest.fn(), showError: jest.fn() })
export const LineChart = () => <div data-testid="mock-line-chart">Chart</div>
export const StackedAreaChart = () => <div data-testid="mock-stacked-area-chart">AreaChart</div>
export const HBarList = () => <div data-testid="mock-hbar-list">HBarList</div>
export const money = (amount: number) => `$${amount.toFixed(2)}`
export const moneyShort = (amount: number) => `${amount}`
export const SkeletonBlock = () => <div data-testid="mock-skeleton-block">Skeleton</div>
export const ConfirmDialog = () => <div data-testid="mock-confirm-dialog">Confirm</div>
export const DateRangePicker = () => <div data-testid="mock-date-range-picker">DateRangePicker</div>