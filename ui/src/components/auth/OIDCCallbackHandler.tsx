import { useEffect } from 'react'
import { useAuthStore } from '@/store/auth'

export function OIDCCallbackHandler() {
  const { setToken } = useAuthStore()

  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')
      const state = params.get('state')
      const error = params.get('error')

      if (error) {
        window.location.href = `/login?error=oidc_failed&detail=${encodeURIComponent(error)}`
        return
      }

      if (!code || !state) {
        window.location.href = '/login?error=invalid_callback'
        return
      }

      try {
        // Get provider_id from sessionStorage (set during login)
        const providerId = sessionStorage.getItem('oidc_provider_id')
        if (!providerId) throw new Error('Provider ID not found')

        const response = await fetch('/api/v1/auth/oidc/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider_id: providerId, code, state }),
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.detail || 'Authentication failed')
        }

        const data = await response.json()
        sessionStorage.removeItem('oidc_provider_id')
        setToken(data.token)
        window.location.href = '/'
      } catch (error) {
        const detail = error instanceof Error ? error.message : 'Unknown error'
        window.location.href = `/login?error=oidc_failed&detail=${encodeURIComponent(detail)}`
      }
    }

    handleCallback()
  }, [setToken])

  return <div>Processing authentication...</div>
}
