import React, { useEffect, useRef, useCallback } from 'react';
import { Icon } from './Icon';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
}

let drawerCounter = 0;

export function Drawer({ open, onClose, title, subtitle, children, footer, width = 480 }: DrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useRef(`fn-drawer-title-${++drawerCounter}`);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }
    if (e.key === 'Tab' && drawerRef.current) {
      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement;
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => {
      if (drawerRef.current) {
        const firstFocusable = drawerRef.current.querySelector<HTMLElement>(
          'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          drawerRef.current.focus();
        }
      }
    });
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [open, handleKeyDown]);

  return (
    <>
      <div className={`fn-drawer-scrim ${open ? 'is-open' : ''}`} onClick={onClose} aria-hidden="true" />
      <aside
        ref={drawerRef}
        className={`fn-drawer ${open ? 'is-open' : ''}`}
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId.current}
        tabIndex={-1}
      >
        <div className="fn-drawer-head">
          <div>
            <div className="fn-drawer-title" id={titleId.current}>{title}</div>
            {subtitle && <div className="fn-drawer-sub">{subtitle}</div>}
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close drawer">
            <Icon name="x" size={16} aria-hidden />
          </button>
        </div>
        <div className="fn-drawer-body">{children}</div>
        {footer && <div className="fn-drawer-foot">{footer}</div>}
      </aside>
    </>
  );
}