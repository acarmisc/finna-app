/**@description Login screen component for FinOps Console
 * Follows the design system from Console.css and common components
 */

import React, { useState, useEffect } from 'react';
import { getApiClient } from '../services/apiClient';
import { APIScreen, LoadingScreen } from '../components/common/APIScreen';

export function LoginScreen() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(true);

  useEffect(() => {
    // Check backend health on mount
    getApiClient().healthCheck()
      .then(result => {
        setBackendHealthy(!result.error);
        if (result.error) {
          console.warn('Backend health check failed:', result.error);
        }
      })
      .catch(err => {
        console.error('Backend health check error:', err);
        setBackendHealthy(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const client = getApiClient();
      const response = await client.login(username, password);

      if (response.error) {
        setError(response.error.message || 'Login failed');
        return;
      }

      // Success - reload to get auth token
      window.location.reload();
    } catch (err) {
      setError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  if (!backendHealthy) {
    return (
      <div className="fn-app">
        <LoadingScreen message="Connecting to FinOps Console backend..." />
      </div>
    );
  }

  return (
    <div className="fn-app">
      <div className="fn-screen" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        padding: 'var(--s-8)'
      }}>
        <div 
          className="fn-panel" 
          style={{ 
            maxWidth: '420px', 
            width: '100%',
            padding: 'var(--s-6)'
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 'var(--s-6)' }}>
            <h1 style={{ 
              fontSize: 'var(--fs-24)', 
              fontWeight: 'var(--fw-semi)', 
              marginBottom: 'var(--s-2)',
              color: 'var(--fg)'
            }}>
              FinOps Console
            </h1>
            <p style={{ 
              fontSize: 'var(--fs-13)', 
              color: 'var(--fg-subtle)' 
            }}>
              Multi-cloud cost management platform
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-4)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)' }}>
              <label htmlFor="username" style={{ 
                fontSize: 'var(--fs-13)', 
                fontWeight: 'var(--fw-med)',
                color: 'var(--fg)'
              }}>
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                style={{
                  padding: 'var(--s-3) var(--s-4)',
                  fontSize: 'var(--fs-13)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-surface)',
                  color: 'var(--fg)',
                  outline: 'none',
                  transition: 'border-color var(--dur-fast)'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--ring)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)' }}>
              <label htmlFor="password" style={{ 
                fontSize: 'var(--fs-13)', 
                fontWeight: 'var(--fw-med)',
                color: 'var(--fg)'
              }}>
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                style={{
                  padding: 'var(--s-3) var(--s-4)',
                  fontSize: 'var(--fs-13)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-surface)',
                  color: 'var(--fg)',
                  outline: 'none',
                  transition: 'border-color var(--dur-fast)'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--ring)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
              />
            </div>

            {error && (
              <div style={{
                padding: 'var(--s-3) var(--s-4)',
                background: 'var(--danger-weak)',
                color: 'var(--danger)',
                borderRadius: 'var(--radius)',
                fontSize: 'var(--fs-13)',
                border: '1px solid var(--danger)',
                textAlign: 'center'
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="fn-btn fn-btn-primary"
              style={{
                height: '40px',
                fontSize: 'var(--fs-14)',
                fontWeight: 'var(--fw-med)',
                marginTop: 'var(--s-2)',
                justifySelf: 'center'
              }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-2)' }}>
                  <span className="fn-dot" style={{ 
                    width: '12px', 
                    height: '12px', 
                    backgroundColor: 'currentColor',
                    borderRadius: '50%',
                    animation: 'pulse 1s infinite'
                  }}></span>
                  Logging in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div style={{ 
            marginTop: 'var(--s-6)', 
            padding: 'var(--s-4)', 
            background: 'var(--bg-accent)', 
            borderRadius: 'var(--radius)',
            fontSize: 'var(--fs-12)',
            color: 'var(--fg-subtle)',
            textAlign: 'center',
            display: backendHealthy ? 'flex' : 'none',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--s-2)'
          }}>
            <span className="fn-dot" style={{ color: 'var(--success)' }}></span>
            Backend: Online
          </div>
        </div>
      </div>
    </div>
  );
}

// Auto-check health on load
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  // This will run when module loads
  const checkInterval = setInterval(() => {
    if (document.readyState === 'complete') {
      clearInterval(checkInterval);
    }
  }, 100);
}
