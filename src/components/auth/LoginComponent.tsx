import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/auth'

interface LoginComponentProps {
  onLoginSuccess?: () => void
}

export default function LoginComponent({ onLoginSuccess }: LoginComponentProps) {
  const { setToken, checkAuth, login } = useAuthStore()
  const [user, setUser] = useState('admin')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    if (!pw) {
      setErr('enter a password to authenticate')
      return
    }
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      const token = 'admin'
      setToken(token)
      onLoginSuccess?.()
    }, 700)
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-hd">
          <span className="caret">&gt; </span>finna login<span className="cursor" />
        </div>
        <form className="login-bd" onSubmit={submit}>
          <div className="field">
            <div className="label">username</div>
            <input
              className={`inp ${err ? 'error' : ''}`}
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="user@domain.com"
            />
          </div>
          <div className="field">
            <div className="label">password</div>
            <input
              type="password"
              className={`inp ${err ? 'error' : ''}`}
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              placeholder="••••••••"
            />
            {err && <div className="hint error">// {err}</div>}
          </div>
          <div className="field" style={{ marginTop: 20 }}>
            <Button variant="default" type="submit" disabled={loading} className="bracket block">
              {loading ? 'authenticating…' : 'authenticate'}
            </Button>
          </div>
          <div className="ascii-divider" style={{ textAlign: 'center', marginTop: 16 }}>
            · · · · · ·
          </div>
          <div className="hint" style={{ textAlign: 'center', marginTop: 8 }}>
            POST /api/v1/auth/token
          </div>
        </form>
        <div className="login-foot">
          <span>v0.1.0</span>
        </div>
      </div>
    </div>
  )
}
