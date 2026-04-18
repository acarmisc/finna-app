import React from 'react';
import { Icon } from './Icon';

interface ButtonProps {
  variant?: 'primary' | 'outline' | 'ghost';
  size?: 'md' | 'sm' | 'xs';
  children?: React.ReactNode;
  onClick?: (e: React.MouseEvent) => void;
  icon?: string;
  iconRight?: string;
  disabled?: boolean;
  title?: string;
  type?: 'button' | 'submit' | 'reset';
  'aria-label'?: string;
  'aria-pressed'?: boolean;
}

export function Button({
  variant = 'outline',
  size = 'md',
  children,
  onClick,
  icon,
  iconRight,
  disabled,
  title,
  type = 'button',
  'aria-label': ariaLabel,
  'aria-pressed': ariaPressed,
}: ButtonProps) {
  const sizeClass = size === 'sm' ? 'fn-btn-sm' : size === 'xs' ? 'fn-btn-xs' : '';
  const isIconOnly = !children;
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`fn-btn fn-btn-${variant} ${sizeClass}`}
      aria-label={isIconOnly && !ariaLabel && title ? title : ariaLabel || undefined}
      aria-pressed={ariaPressed}
    >
      {icon && <Icon name={icon} size={size === 'sm' || size === 'xs' ? 13 : 14} aria-hidden />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === 'sm' || size === 'xs' ? 13 : 14} aria-hidden />}
    </button>
  );
}
