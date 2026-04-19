/**
 * Component: APIScreen
 * A reusable screen wrapper that handles API data loading and errors
 */

import React, { ReactNode } from 'react';
import { getApiClient } from '../services/apiClient';
import { ToastTone } from '../types';

interface APIScreenProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  onLoadError?: (error: Error) => void;
}

export function APIScreen({ title, subtitle, actions, children, onLoadError }: APIScreenProps) {
  const [healthError, setHealthError] = useState<Error | null>(null);

  useEffect(() => {
    getApiClient().healthCheck()
      .then(result => {
        if (result.error) {
          const error = new Error(result.error.message || 'Backend connection failed');
          setHealthError(error);
          if (onLoadError) {
            onLoadError(error);
          }
        }
      })
      .catch(setHealthError);
  }, [onLoadError]);

  if (healthError) {
    return (
      <div className="fn-screen has-error">
        <div className="error-banner">
          <h2>Backend Connection Required</h2>
          <p>The frontend cannot connect to the backend API.</p>
          <div className="actions">
            <button 
              onClick={() => window.location.reload()} 
              className="btn btn-outline"
            >
              Retry Connection
            </button>
            <a 
              href="http://localhost:8000" 
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
            >
              Start Backend Server
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fn-screen">
      {healthError && (
        <div className="error-bar">
          <span>Error</span>
        </div>
      )}
      
      <header className="fn-screen-header">
        <div className="screen-title">
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="screen-actions">{actions}</div>}
      </header>

      <main className="fn-screen-content">
        {children}
      </main>
    </div>
  );
}

// Loading state component
export function LoadingScreen({ message = 'Loading data...' }: { message?: string }) {
  return (
    <div className="loading-screen">
      <div className="spinner"></div>
      <p>{message}</p>
    </div>
  );
}

// Error boundary component
export function ErrorBoundary({ children }: { children: ReactNode }) {
  const [hasError, setHasError] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  if (hasError) {
    return (
      <div className="error-screen">
        <div className="error-content">
          <h2>Something went wrong</h2>
          {error && <p>{error.message}</p>}
          <button 
            onClick={() => {
              setHasError(false);
              setError(null);
              window.location.reload();
            }}
            className="btn btn-primary"
          >
            Reload Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <React.ErrorBoundary
      fallbackRender={({ error }) => {
        setHasError(true);
        setError(error);
        return null;
      }}
    >
      {children}
    </React.ErrorBoundary>
  );
}

// Toast notification system
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const pushToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2, 8);
    setToasts(ts => [...ts, { id, ...toast }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(ts => ts.filter(t => t.id !== id));
  }, []);

  return { toasts, pushToast, dismissToast };
}
