import React, { useEffect, useRef } from 'react';

interface IconProps {
  name: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function Icon({ name, size = 16, className = '', style }: IconProps) {
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
    />
  );
}
