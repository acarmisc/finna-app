import React from 'react';

interface SettingsSectionProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function SettingsSection({
  title,
  children,
  className = ''
}: SettingsSectionProps) {
  return (
    <div className={`${className} mb-6`}>
      <h2 className="text-xs font-mono uppercase tracking-widest text-muted-foreground mb-4">
        {title}
      </h2>
      <div className="border border-border p-4">{children}</div>
    </div>
  );
}