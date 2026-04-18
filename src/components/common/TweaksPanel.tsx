import React, { useEffect, useRef } from 'react';
import { Icon } from './Icon';
import type { Theme, Density, Accent } from '../../types';

interface TweaksPanelProps {
  open: boolean;
  onClose: () => void;
  theme: Theme;
  density: Density;
  accent: Accent;
  setTheme: (t: Theme) => void;
  setDensity: (d: Density) => void;
  setAccent: (a: Accent) => void;
}

const ACCENTS: { id: Accent; label: string; color: string }[] = [
  { id: 'green', label: 'Green', color: 'oklch(0.58 0.14 150)' },
  { id: 'indigo', label: 'Indigo', color: 'oklch(0.52 0.18 275)' },
  { id: 'amber', label: 'Amber', color: 'oklch(0.70 0.17 75)' },
  { id: 'slate', label: 'Slate', color: 'oklch(0.40 0.020 265)' },
];

export function TweaksPanel({ open, onClose, theme, density, accent, setTheme, setDensity, setAccent }: TweaksPanelProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, onClose]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'finna-tweaks') {
        const { theme: t, density: d, accent: a } = e.data;
        if (t === 'light' || t === 'dark') setTheme(t);
        if (d === 'compact' || d === 'cozy') setDensity(d);
        if (['green', 'indigo', 'amber', 'slate'].includes(a)) setAccent(a as Accent);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [setTheme, setDensity, setAccent]);

  if (!open) return null;

  return (
    <div className="fn-tweaks-overlay" onClick={onClose} aria-hidden="true">
      <div className="fn-tweaks-panel" ref={ref} role="dialog" aria-label="Appearance settings" onClick={e => e.stopPropagation()}>
        <div className="fn-tweaks-head">
          <h3>Appearance</h3>
          <button className="fn-iconbtn" onClick={onClose} aria-label="Close">
            <Icon name="x" size={16} aria-hidden />
          </button>
        </div>

        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Density</div>
          <div className="fn-seg">
            <button className={`fn-seg-btn ${density === 'compact' ? 'is-active' : ''}`} onClick={() => setDensity('compact')}>Compact</button>
            <button className={`fn-seg-btn ${density === 'cozy' ? 'is-active' : ''}`} onClick={() => setDensity('cozy')}>Cozy</button>
          </div>
        </div>

        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Theme</div>
          <div className="fn-seg">
            <button className={`fn-seg-btn ${theme === 'light' ? 'is-active' : ''}`} onClick={() => setTheme('light')}>
              <Icon name="sun" size={12} aria-hidden /> Light
            </button>
            <button className={`fn-seg-btn ${theme === 'dark' ? 'is-active' : ''}`} onClick={() => setTheme('dark')}>
              <Icon name="moon" size={12} aria-hidden /> Dark
            </button>
          </div>
        </div>

        <div className="fn-tweak-section">
          <div className="fn-tweak-label">Accent</div>
          <div className="fn-tweaks-accent-row">
            {ACCENTS.map(ac => (
              <button
                key={ac.id}
                className={`fn-accent-swatch ${accent === ac.id ? 'is-active' : ''}`}
                onClick={() => setAccent(ac.id)}
                style={{ '--swatch': ac.color } as React.CSSProperties}
                aria-label={`Accent: ${ac.label}`}
                title={ac.label}
              >
                <span className="fn-accent-dot" />
                <span>{ac.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}