import React, { useEffect, useRef } from 'react';

interface IconProps {
  name: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
  'aria-hidden'?: boolean;
  'aria-label'?: string;
}

export function Icon({
  name,
  size = 16,
  className = '',
  style,
  'aria-hidden': ariaHidden = true,
  'aria-label': ariaLabel,
}: IconProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).lucide) {
      (window as any).lucide.createIcons({
        icons: undefined,
        attrs: {},
        nameAttr: 'data-lucide',
      });
    }
  }, [name]);

  const isDecorative = ariaHidden !== false && !ariaLabel;

  return (
    <i
      ref={ref}
      data-lucide={name}
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