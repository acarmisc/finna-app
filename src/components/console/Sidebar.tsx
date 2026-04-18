import React from 'react';
import { Icon } from '../common/Icon';
import { Kbd } from '../common/Kbd';
import './Sidebar.css';

interface NavItem {
  id: string;
  icon: string;
  label: string;
  badge?: number;
}

interface SidebarProps {
  current: string;
  onNav: (id: string) => void;
  onOpenCmd: () => void;
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', icon: 'gauge', label: 'Dashboard' },
  { id: 'explorer', icon: 'chart-line', label: 'Cost explorer' },
  { id: 'connections', icon: 'plug', label: 'Connections', badge: 1 },
  { id: 'alerts', icon: 'bell', label: 'Alerts', badge: 3 },
  { id: 'runs', icon: 'database', label: 'Run log' },
  { id: 'budgets', icon: 'wallet', label: 'Budgets' },
  { id: 'settings', icon: 'settings', label: 'Settings' },
];

export function Sidebar({ current, onNav, onOpenCmd, collapsed, onToggle }: SidebarProps) {
  return (
    <aside className={`fn-sidebar ${collapsed ? 'is-collapsed' : ''}`}>
      <div className="fn-brand">
        <div className="fn-mark">F</div>
        {!collapsed && <span>Finna</span>}
        <button
          className="fn-iconbtn fn-brand-toggle"
          onClick={onToggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <Icon name={collapsed ? 'panel-left-open' : 'panel-left-close'} size={14} />
        </button>
      </div>

      {!collapsed ? (
        <button className="fn-cmdk-trigger" onClick={onOpenCmd}>
          <Icon name="search" size={14} />
          <span>Search & jump</span>
          <span className="fn-cmdk-trigger-kbd">
            <Kbd>⌘K</Kbd>
          </span>
        </button>
      ) : (
        <button
          className="fn-nav-item"
          onClick={onOpenCmd}
          title="Search & jump (⌘K)"
          aria-label="Search & jump"
        >
          <Icon name="search" size={16} />
        </button>
      )}

      <nav>
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            title={collapsed ? item.label : undefined}
            className={`fn-nav-item ${current === item.id ? 'is-active' : ''}`}
            onClick={() => onNav(item.id)}
          >
            <Icon name={item.icon} size={16} />
            {!collapsed && <span>{item.label}</span>}
            {!collapsed && item.badge && (
              <span className={`fn-nav-badge ${item.id === 'alerts' ? 'is-err' : ''}`}>
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="fn-sidebar-foot">
        {!collapsed && (
          <div className="fn-runtime">
            <div className="fn-runtime-row">
              <span className="fn-runtime-lbl">Next extraction</span>
              <span className="fn-runtime-val mono">02:00 UTC</span>
            </div>
            <div className="fn-runtime-row">
              <span className="fn-runtime-lbl">ECB rate</span>
              <span className="fn-runtime-val mono">1 EUR = 1.082 USD</span>
            </div>
          </div>
        )}
        <div className="fn-org">
          <div className="fn-org-dot">A</div>
          {!collapsed && (
            <>
              <div className="fn-org-txt">
                <div className="fn-org-name">Acme Platform</div>
                <div className="fn-org-meta">7 connections · 2 LLM</div>
              </div>
              <Icon
                name="chevrons-up-down"
                size={14}
                style={{ color: 'var(--fg-subtle)', marginLeft: 'auto' }}
              />
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
