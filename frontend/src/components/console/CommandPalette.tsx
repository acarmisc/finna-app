import React, { useState, useEffect, useRef } from 'react';
import { Icon } from '../common/Icon';
import { Kbd } from '../common/Kbd';
import './CommandPalette.css';

interface Screen {
  id: string;
  label: string;
  icon: string;
}

interface Command {
  kind: 'nav' | 'action';
  icon: string;
  label: string;
  hint: string;
  run: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNav: (id: string) => void;
  screens: Screen[];
}

export function CommandPalette({ open, onClose, onNav, screens }: CommandPaletteProps) {
  const [q, setQ] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 10);
    } else {
      setQ('');
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const commands: Command[] = [
    ...screens.map(s => ({
      kind: 'nav' as const,
      icon: s.icon,
      label: `Go to ${s.label}`,
      hint: s.id,
      run: () => {
        onNav(s.id);
        onClose();
      },
    })),
    { kind: 'action' as const, icon: 'play', label: 'Run all extractors now', hint: 'action', run: onClose },
    { kind: 'action' as const, icon: 'plus', label: 'New connection', hint: 'action', run: () => { onNav('connections'); onClose(); } },
    { kind: 'action' as const, icon: 'download', label: 'Export cost_records as CSV', hint: 'action', run: onClose },
    { kind: 'action' as const, icon: 'refresh-cw', label: 'Refresh exchange rates', hint: 'action', run: onClose },
  ];

  const filtered = q ? commands.filter(c => c.label.toLowerCase().includes(q.toLowerCase())) : commands;

  return (
    <div className="fn-scrim" onClick={onClose}>
      <div className="fn-cmdk" onClick={e => e.stopPropagation()}>
        <div className="fn-cmdk-input">
          <Icon name="search" size={16} />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Search or run a command…"
          />
          <Kbd>esc</Kbd>
        </div>
        <div className="fn-cmdk-list">
          {filtered.length === 0 && <div className="fn-cmdk-empty">No matches.</div>}
          {filtered.map((c, i) => (
            <button key={i} className="fn-cmdk-item" onClick={c.run}>
              <Icon name={c.icon} size={14} />
              <span>{c.label}</span>
              <span className="fn-cmdk-kind">{c.hint}</span>
            </button>
          ))}
        </div>
        <div className="fn-cmdk-foot">
          <span>
            <Kbd>↑↓</Kbd> navigate
          </span>
          <span>
            <Kbd>↵</Kbd> run
          </span>
          <span>
            <Kbd>⌘K</Kbd> toggle
          </span>
        </div>
      </div>
    </div>
  );
}
