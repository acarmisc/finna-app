import React from 'react';
import { Icon } from './Icon';

interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="fn-breadcrumb" aria-label="Breadcrumb">
      {items.map((it, i) => (
        <React.Fragment key={i}>
          {i > 0 && <Icon name="chevron-right" size={12} className="fn-bc-sep" />}
          {it.onClick ? (
            <button className="fn-bc-link" onClick={it.onClick}>
              {it.label}
            </button>
          ) : (
            <span className="fn-bc-cur">{it.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
