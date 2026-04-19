import React, { useState, useEffect } from 'react';
import { getApiClient } from '../services/apiClient';

export function LoginScreen() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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

      // Success - redirect would be handled by parent
      window.location.reload();
    } catch (err) {
      setError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>FinOps Console</h1>
        <p className="subtitle">Multi-cloud cost management platform</p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="btn btn-primary btn-block">
            {loading ? 'Logging in...' : 'Sign In'}
          </button>
        </form>

        <div className="backend-status">
          <span className="dot"></span>
          <span>Backend: Checking...</span>
        </div>
      </div>
    </div>
  );
}

// Health check for backend connection
export function checkBackendHealth(): Promise<boolean> {
  const client = getApiClient();
  return client.healthCheck()
    .then(result => {
      if (result.error) {
        console.warn('Backend health check failed:', result.error);
        return false;
      }
      console.log('Backend is healthy:', result.data);
      return true;
    })
    .catch(err => {
      console.error('Backend health check error:', err);
      return false;
    });
}

// Auto-check health on load
if (typeof window !== 'undefined') {
  checkBackendHealth();
}
