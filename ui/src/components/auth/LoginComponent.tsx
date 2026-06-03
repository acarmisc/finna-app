import { useState, useEffect } from 'react'
import { useAuthStore } from '@/store/auth'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'
import { useTheme } from '@/contexts/ThemeContext'

interface LoginComponentProps {
  onLoginSuccess?: () => void
}

/**
 * Allowlist of trusted redirect origins.
 * Prevents open redirect vulnerabilities by validating redirect_uri against this list.
 * Defaults to the current origin; can be overridden via environment variable.
 */
const ALLOWED_REDIRECT_ORIGINS = (
  import.meta.env.VITE_ALLOWED_REDIRECT_ORIGINS?.split(',') || [window.location.origin]
).map(origin => origin.trim()).filter(Boolean)

/**
 * Safely validate and redirect to a URL.
 * Ensures the target origin is in the allowlist before redirecting.
 * Falls back to '/' if the URL origin is not trusted.
 */
function safeRedirect(targetUrl: string): void {
  try {
    const parsed = new URL(targetUrl, window.location.origin)
    if (ALLOWED_REDIRECT_ORIGINS.includes(parsed.origin)) {
      window.location.href = targetUrl
      return
    }
  } catch {
    // Invalid URL; fall back to safe redirect
  }
  // Fallback: redirect to home
  window.location.href = '/'
}

const SSO_PROVIDERS = [
  {
    id: 'github',
    name: 'Continue with GitHub',
    meta: 'OAuth',
    svg: (
      <svg viewBox="0 0 18 18" width="18" height="18" fill="currentColor">
        <path d="M9 .5a8.5 8.5 0 0 0-2.69 16.57c.43.08.59-.18.59-.41 0-.2-.01-.74-.01-1.45-2.4.52-2.9-1.16-2.9-1.16-.4-1-.97-1.27-.97-1.27-.79-.54.06-.53.06-.53.87.06 1.33.9 1.33.9.78 1.33 2.04.95 2.54.72.08-.56.3-.95.55-1.17-1.92-.22-3.94-.96-3.94-4.27 0-.94.34-1.71.89-2.31-.09-.22-.39-1.1.08-2.29 0 0 .72-.23 2.36.88a8.2 8.2 0 0 1 4.3 0c1.64-1.11 2.36-.88 2.36-.88.47 1.19.17 2.07.08 2.29.55.6.89 1.37.89 2.31 0 3.32-2.02 4.05-3.95 4.26.31.27.59.8.59 1.62 0 1.17-.01 2.11-.01 2.4 0 .23.16.5.6.41A8.5 8.5 0 0 0 9 .5z" />
      </svg>
    ),
  },
] as const

export default function LoginComponent({ onLoginSuccess }: LoginComponentProps) {
  const { setToken, isAuthenticated } = useAuthStore()
  const [showEmail, setShowEmail] = useState(false)
  const [user, setUser] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const { resolvedTheme, toggleTheme } = useTheme()
  const [oidcProviders, setOidcProviders] = useState<any[]>([])

  useEffect(() => {
    fetchOidcProviders()
    const hash = window.location.hash
    const params = new URLSearchParams(hash.slice(1))
    const code = params.get('code')
    if (code && !isAuthenticated) {
      handleOAuthCallback(code)
      window.location.hash = ''
    }
  }, [])

  const fetchOidcProviders = async () => {
    try {
      const response = await fetch('/api/v1/auth/oidc/providers')
      if (response.ok) {
        setOidcProviders(await response.json())
      }
    } catch (e) {
      console.error('Failed to fetch OIDC providers', e)
    }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    if (!user || !pw) {
      setErr('Enter email and password to continue')
      return
    }
    setLoadingId('email')
    try {
      const response = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pw }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setErr(data.detail || 'Invalid credentials')
        setLoadingId(null)
        return
      }
      const data = await response.json()
      setToken(data.token)
      onLoginSuccess?.()
    } catch {
      setErr('Connection error')
      setLoadingId(null)
    }
  }

  const ssoLogin = async (id: string) => {
    if (id === 'github') {
      setLoadingId(id)
      try {
        const response = await fetch('/api/v1/auth/github')
        const data = await response.json()
        if (!response.ok || data.error) {
          setErr(data.error || 'GitHub login not configured')
          setLoadingId(null)
          return
        }
        // Validate redirect URL against allowlist to prevent open redirect
        safeRedirect(data.url)
      } catch {
        setErr('Connection error')
        setLoadingId(null)
      }
      return
    }
    setErr('This login method is not available')
  }

  const oidcLogin = async (providerId: string) => {
    setLoadingId(providerId)
    try {
      const response = await fetch('/api/v1/auth/oidc/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId }),
      })
      if (!response.ok) {
        setErr('Failed to initiate login')
        setLoadingId(null)
        return
      }
      const data = await response.json()
      sessionStorage.setItem('oidc_provider_id', providerId)
      // Validate redirect URL against allowlist to prevent open redirect
      safeRedirect(data.authorization_url)
    } catch (e) {
      setErr('Connection error')
      setLoadingId(null)
    }
  }

  const handleOAuthCallback = async (code: string) => {
    setLoadingId('github')
    try {
      const response = await fetch('/api/v1/auth/github/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        setErr(data.detail || 'Login failed')
        setLoadingId(null)
        return
      }
      const data = await response.json()
      setToken(data.token)
      onLoginSuccess?.()
    } catch {
      setErr('Connection error')
      setLoadingId(null)
    }
  }

  return (
    <div className="login-wrap">
      <aside className="login-brand">
        <div className="login-brand-mark">
          <span className="caret">&gt;</span>
          <span>finna</span>
        </div>
        <div className="login-brand-headline">
          <h1>Cloud + LLM costs, <span className="accent">in one console.</span></h1>
          <p>Track Azure, GCP and LLM spend, set budgets per project, and catch anomalies before they hit your bill.</p>
        </div>
        <div className="login-brand-stats">
          <div className="item"><div className="v">$1.2M</div><div className="l">Tracked monthly</div></div>
          <div className="item"><div className="v">3</div><div className="l">Cloud + LLM</div></div>
          <div className="item"><div className="v">99.9%</div><div className="l">Extractor uptime</div></div>
        </div>
      </aside>

      <div className="login-pane">
        <div className="login-card">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} theme`}
          >
            <Icon name={resolvedTheme === 'dark' ? 'sun' : 'moon'} size={16} />
          </button>
          <h2 className="title">Sign in to Finna</h2>
          <p className="subtitle">Use your work account to access the FinOps console.</p>

          <div className="sso-list">
            {SSO_PROVIDERS.map(p => (
              <button key={p.id} className="sso-btn" onClick={() => ssoLogin(p.id)} disabled={!!loadingId}>
                <span className="ico">{p.svg}</span>
                <span className="name">{loadingId === p.id ? 'Redirecting…' : p.name}</span>
                <span className="meta">{p.meta}</span>
              </button>
            ))}
            {oidcProviders.map(p => (
              <button key={p.id} className="sso-btn" onClick={() => oidcLogin(p.id)} disabled={!!loadingId}>
                <span className="ico">🔐</span>
                <span className="name">{loadingId === p.id ? 'Redirecting…' : `Sign in with ${p.name}`}</span>
                <span className="meta">OIDC</span>
              </button>
            ))}
          </div>

          <div className="login-divider"><span>or</span></div>

          {!showEmail ? (
            <button className="login-email-toggle" onClick={() => setShowEmail(true)}>
              Sign in with email and password
            </button>
          ) : (
            <form className="login-email-form" onSubmit={submit}>
              <div className="field">
                <div className="label">Email</div>
                <input
                  className={`inp ${err ? 'error' : ''}`}
                  value={user}
                  onChange={e => setUser(e.target.value)}
                  placeholder="you@company.com"
                  autoFocus
                />
              </div>
              <div className="field">
                <div className="label">Password</div>
                <input
                  type="password"
                  className={`inp ${err ? 'error' : ''}`}
                  value={pw}
                  onChange={e => setPw(e.target.value)}
                  placeholder="••••••••"
                />
                <div className="row" style={{ marginTop: 6, justifyContent: 'flex-end' }}>
                  <a href="#" onClick={e => e.preventDefault()} style={{ fontSize: '11px' }}>Forgot password?</a>
                </div>
                {err && <div className="hint error" style={{ marginTop: 6 }}>{err}</div>}
              </div>
              <Button variant="primary" type="submit" bracket block disabled={loadingId === 'email'}>
                {loadingId === 'email' ? 'Authenticating…' : 'Sign in'}
              </Button>
              <button type="button" className="login-email-toggle" onClick={() => setShowEmail(false)} style={{ marginTop: 0 }}>
                ← Back to SSO options
              </button>
            </form>
          )}

          <div className="login-foot">
            <span>Need an account? <a href="#" onClick={e => e.preventDefault()}>Contact admin</a></span>
            <span className="mono">v2.4.1</span>
          </div>
        </div>
      </div>
    </div>
  )
}
