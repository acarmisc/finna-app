import React from 'react';

interface NotificationToggleProps {
  label: string;
  checked: boolean;
  onChange: () => void;
  status?: 'firing' | 'pending';
  service?: 'email' | 'telegram' | 'slack';
}

export function NotificationToggle({
  label,
  checked,
  onChange,
  status,
  service
}: NotificationToggleProps) {
  const fullLabel = service && status ? `${service} · ${status} alerts` : label;

  return (
    <div className="flex items-center justify-between">
      <label className="text-sm text-foreground cursor-pointer">{fullLabel}</label>
      <button
        onClick={onChange}
        className="w-9 h-5 border border-border relative transition-colors"
        style={{
          background: checked ? 'var(--accent)' : 'var(--surface-2)',
        }}
        aria-label={`${fullLabel} toggle`}
        role="switch"
        aria-checked={checked}
      >
        <span className="absolute top-0.5 transition-all"
          style={{
            left: checked ? '18px' : '0px',
            color: 'var(--bg)'
          }}>
          ●
        </span>
      </button>
    </div>
  );
}