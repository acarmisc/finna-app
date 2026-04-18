import React from 'react';
import { Icon } from './Icon';
import { Button } from './Button';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="fn-error-state" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      padding: '40px 24px',
      textAlign: 'center',
    }}>
      <Icon name="alert-triangle" size={32} style={{ color: 'var(--fg-muted)' }} />
      <div style={{ color: 'var(--fg-subtle)', maxWidth: 400 }}>{message}</div>
      {onRetry && (
        <Button variant="outline" size="sm" icon="refresh-cw" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
