import React from 'react';

interface TopBarProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
}

export function TopBar({ title, subtitle, actions, breadcrumb }: TopBarProps) {
  return (
    <header className="fn-topbar">
      <div className="fn-topbar-l">
        {breadcrumb && <div className="fn-crumb">{breadcrumb}</div>}
        <div className="fn-topbar-title">{title}</div>
        {subtitle && <div className="fn-topbar-sub">{subtitle}</div>}
      </div>
      {actions && <div className="fn-topbar-actions">{actions}</div>}
    </header>
  );
}
