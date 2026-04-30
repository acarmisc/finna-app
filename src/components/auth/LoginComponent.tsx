import { useState } from 'react'
import { useAuthStore } from '@/store/auth'
import { Button } from '@/components/shared/Button'
import { Icon } from '@/components/shared/Icon'

interface LoginComponentProps {
  onLoginSuccess?: () => void
}

const SSO_PROVIDERS = [
  {
    id: 'google',
    name: 'Continue with Google',
    meta: 'OAuth',
    svg: (
      <svg viewBox="0 0 18 18" width="18" height="18">
        <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.79 2.71v2.26h2.9c1.7-1.56 2.69-3.87 2.69-6.62z" />
        <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.9-2.26c-.81.54-1.84.86-3.06.86-2.36 0-4.36-1.59-5.07-3.74H.96v2.34A8.99 8.99 0 0 0 9 18z" />
        <path fill="#FBBC05" d="M3.93 10.68A5.4 5.4 0 0 1 3.64 9c0-.58.1-1.15.29-1.68V4.98H.96A8.99 8.99 0 0 0 0 9c0 1.45.35 2.83.96 4.02l2.97-2.34z" />
        <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58A8.99 8.99 0 0 0 9 0 9 9 0 0 0 .96 4.98L3.93 7.32C4.64 5.17 6.64 3.58 9 3.58z" />
      </svg>
    ),
  },
  {
    id: 'microsoft',
    name: 'Continue with Microsoft',
    meta: 'OAuth',
    svg: (
      <svg viewBox="0 0 18 18" width="18" height="18">
        <rect x="1" y="1" width="7.5" height="7.5" fill="#F25022" />
        <rect x="9.5" y="1" width="7.5" height="7.5" fill="#7FBA00" />
        <rect x="1" y="9.5" width="7.5" height="7.5" fill="#00A4EF" />
        <rect x="9.5" y="9.5" width="7.5" height="7.5" fill="#FFB900" />
      </svg>
    ),
  },
  {
    id: 'okta',
    name: 'Continue with Okta',
    meta: 'SAML',
    svg: (
      <svg viewBox="0 0 18 18" width="18" height="18">
        <circle cx="9" cy="9" r="7" fill="none" stroke="#007DC1" strokeWidth="3" />
      </svg>
    ),
  },
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
  const { setToken } = useAuthStore()
  const [showEmail, setShowEmail] = useState(false)
  const [user, setUser] = useState('finops@acme.co')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    if (!pw) {
      setErr('Enter a password to continue')
      return
    }
    setLoadingId('email')
    setTimeout(() => {
      setLoadingId(null)
      setToken('admin')
      onLoginSuccess?.()
    }, 600)
  }

  const ssoLogin = (id: string) => {
    setLoadingId(id)
    setTimeout(() => {
      setLoadingId(null)
      setToken('admin')
      onLoginSuccess?.()
    }, 700)
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
            <button className="sso-btn" onClick={() => ssoLogin('saml')} disabled={!!loadingId}>
              <span className="ico"><Icon name="key-round" size={16} /></span>
              <span className="name">{loadingId === 'saml' ? 'Redirecting…' : 'SAML SSO'}</span>
              <span className="meta">Enterprise</span>
            </button>
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
                <div className="row" style={{ marginBottom: 6 }}>
                  <span className="label" style={{ margin: 0 }}>Password</span>
                  <a href="#" onClick={e => e.preventDefault()}>Forgot?</a>
                </div>
                <input
                  type="password"
                  className={`inp ${err ? 'error' : ''}`}
                  value={pw}
                  onChange={e => setPw(e.target.value)}
                  placeholder="••••••••"
                />
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
