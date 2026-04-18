import React from 'react';
import { Icon } from '../common/Icon';
import type { Toast } from '../../types';
import './Toaster.css';

interface ToasterProps {
  toasts: Toast[];
  dismiss: (id: string) => void;
}

export function Toaster({ toasts, dismiss }: ToasterProps) {
  const getIcon = (toast: Toast) => {
    if (toast.icon) return toast.icon;
    switch (toast.tone) {
      case 'err':
        return 'alert-triangle';
      case 'ok':
        return 'check-circle-2';
      default:
        return 'info';
    }
  };

  return (
    <div className="fn-toasts">
      {toasts.map(t => (
        <div key={t.id} className={`fn-toast fn-toast-${t.tone || 'info'}`}>
          <Icon name={getIcon(t)} size={16} />
          <div className="fn-toast-body">
            <div className="fn-toast-title">{t.title}</div>
            {t.body && <div className="fn-toast-sub">{t.body}</div>}
          </div>
          <button
            className="fn-iconbtn"
            onClick={() => dismiss(t.id)}
            aria-label="Close"
          >
            <Icon name="x" size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
