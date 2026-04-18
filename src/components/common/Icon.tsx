import React from 'react';
import * as LucideIcons from 'lucide-react';

interface IconProps {
  name: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
  'aria-hidden'?: boolean;
  'aria-label'?: string;
}

const ICON_CACHE: Record<string, React.ComponentType<any>> = {};

function resolveIcon(name: string): React.ComponentType<any> | null {
  if (ICON_CACHE[name]) return ICON_CACHE[name];
  const pascal = name
    .split('-')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join('');
  const IconComp = (LucideIcons as any)[pascal] ?? null;
  ICON_CACHE[name] = IconComp;
  return IconComp;
}

export function Icon({
  name,
  size = 16,
  className = '',
  style,
  'aria-hidden': ariaHidden = true,
  'aria-label': ariaLabel,
}: IconProps) {
  const IconComp = resolveIcon(name);
  const isDecorative = ariaHidden !== false && !ariaLabel;

  if (!IconComp) {
    return (
      <span
        className={className}
        style={{
          width: size,
          height: size,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          ...style,
        }}
        aria-hidden={isDecorative ? true : undefined}
        aria-label={ariaLabel || undefined}
        role={ariaLabel ? 'img' : undefined}
      />
    );
  }

  return (
    <IconComp
      size={size}
      className={className}
      style={{ ...style }}
      aria-hidden={isDecorative ? true : undefined}
      aria-label={ariaLabel || undefined}
      role={ariaLabel ? 'img' : undefined}
    />
  );
}
