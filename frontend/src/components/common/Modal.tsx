import React, { useEffect, useRef, useCallback } from 'react';
import { Icon } from './Icon';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
}

let modalCounter = 0;

export function Modal({ open, onClose, title, subtitle, children, footer, width = 520 }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useRef(`fn-modal-title-${++modalCounter}`);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }
    if (e.key === 'Tab' && modalRef.current) {
      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
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
    const scrollY = window.scrollY;
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => {
      if (modalRef.current) {
        const firstFocusable = modalRef.current.querySelector<HTMLElement>(
          'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          modalRef.current.focus();
        }
      }
    });
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      window.scrollTo(0, scrollY);
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fn-scrim" onClick={onClose}>
      <div
        ref={modalRef}
        className="fn-modal"
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId.current}
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <div className="fn-modal-head">
          <div>
            <div className="fn-modal-title" id={titleId.current}>{title}</div>
            {subtitle && <div className="fn-modal-sub">{subtitle}</div>}
          </div>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close dialog">
            <Icon name="x" size={16} aria-hidden />
          </button>
        </div>
        <div className="fn-modal-body">{children}</div>
        {footer && <div className="fn-modal-foot">{footer}</div>}
      </div>
    </div>
  );
}