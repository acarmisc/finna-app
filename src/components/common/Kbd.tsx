import React from 'react';
import './Kbd.css';

interface KbdProps {
  children: React.ReactNode;
}

export function Kbd({ children }: KbdProps) {
  return <kbd className="fn-kbd">{children}</kbd>;
}
