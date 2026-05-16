import React, { useEffect, useState } from 'react'
import { Button } from '@/components/shared/Button'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'

interface AuthProvider {
  id: string
  name: string
  kind: string
  enabled: boolean
  config: Record<string, any>
  created_at?: string
  last_test_at?: string
  last_test_ok?: boolean
}

interface ProviderConfig {
  issuer: string
  client_id: string
  client_secret: string
  redirect_uri: string
  scopes: string[]
  claim_mappings: Record<string, any>
  auto_provision: boolean
  allowed_email_domains: string[]
}

const PRESETS: Record<string, Partial<ProviderConfig>> = {
  keycloak: {
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {
      username: 'preferred_username',
      email: 'email',
      is_admin: { claim: 'groups', match: 'finna-admins' },
    },
  },
  okta: {
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {
      username: 'preferred_username',
      email: 'email',
      is_admin: { claim: 'groups', match: 'admin' },
    },
  },
  auth0: {
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {
      username: 'nickname',
      email: 'email',
      is_admin: { claim: 'roles', match: 'admin' },
    },
  },
  azure: {
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {
      username: 'upn',
      email: 'email',
      is_admin: { claim: 'groups', match: 'admin' },
    },
  },
  google: {
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {
      username: 'email',
      email: 'email',
    },
  },
}

export function OIDCProvidersSection() {
  const [providers, setProviders] = useState<AuthProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [formData, setFormData] = useState<ProviderConfig>({
    issuer: '',
    client_id: '',
    client_secret: '',
    redirect_uri: window.location.origin + '/auth/oidc/callback',
    scopes: ['openid', 'profile', 'email'],
    claim_mappings: {},
    auto_provision: false,
    allowed_email_domains: [],
  })
  const [providerName, setProviderName] = useState('')
  const [testStatus, setTestStatus] = useState<{ loading: boolean; success?: boolean; error?: string }>({
    loading: false,
  })

  useEffect(() => {
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/v1/auth/providers', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        setProviders(await response.json())
      }
    } catch (e) {
      console.error('Failed to fetch providers', e)
    } finally {
      setLoading(false)
    }
  }

  const openModal = (provider?: AuthProvider) => {
    if (provider) {
      setEditingId(provider.id)
      setProviderName(provider.name)
      setFormData(provider.config as ProviderConfig)
    } else {
      setEditingId(null)
      setProviderName('')
      setFormData({
        issuer: '',
        client_id: '',
        client_secret: '',
        redirect_uri: window.location.origin + '/auth/oidc/callback',
        scopes: ['openid', 'profile', 'email'],
        claim_mappings: {},
        auto_provision: false,
        allowed_email_domains: [],
      })
    }
    setShowModal(true)
  }

  const applyPreset = (presetKey: string) => {
    const preset = PRESETS[presetKey]
    setFormData({ ...formData, ...preset })
  }

  const saveProvider = async () => {
    if (!providerName.trim() || !formData.issuer.trim()) {
      alert('Name and issuer are required')
      return
    }

    try {
      const token = localStorage.getItem('token')
      const method = editingId ? 'PUT' : 'POST'
      const url = editingId ? `/api/v1/auth/providers/${editingId}` : '/api/v1/auth/providers'

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: providerName,
          kind: 'oidc',
          enabled: false,
          config: formData,
        }),
      })

      if (response.ok) {
        setShowModal(false)
        fetchProviders()
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail}`)
      }
    } catch (e) {
      alert('Failed to save provider')
      console.error(e)
    }
  }

  const testProvider = async (providerId: string) => {
    setTestStatus({ loading: true })
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/auth/oidc/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ provider_id: providerId }),
      })

      if (response.ok) {
        setTestStatus({ loading: false, success: true })
        setTimeout(() => setTestStatus({ loading: false }), 3000)
      } else {
        const error = await response.json()
        setTestStatus({ loading: false, error: error.detail })
      }
    } catch (e) {
      setTestStatus({ loading: false, error: 'Test failed' })
    }
  }

  const deleteProvider = async () => {
    if (!deleteId) return
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/v1/auth/providers/${deleteId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        setDeleteId(null)
        fetchProviders()
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail}`)
      }
    } catch (e) {
      alert('Failed to delete provider')
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="card mt-3">
      <div className="card-hd">
        <h3>Authentication</h3>
        <Button variant="primary" size="sm" bracket onClick={() => openModal()}>
          + Add Provider
        </Button>
      </div>

      <div className="card-bd">
        {providers.length === 0 ? (
          <div className="mono muted" style={{ textAlign: 'center', padding: '2rem' }}>
            No OIDC providers configured
          </div>
        ) : (
          <div className="stack stack-3">
            {providers.map((p) => (
              <div key={p.id} className="spread" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{p.name}</div>
                  <div className="mono muted" style={{ fontSize: 11 }}>
                    {p.config.issuer}
                  </div>
                  <div style={{ fontSize: 12, marginTop: '0.5rem' }}>
                    {p.enabled ? (
                      <span className="badge ghost-success">
                        <span className="dot" />
                        Enabled
                      </span>
                    ) : (
                      <span className="badge ghost-muted">Disabled</span>
                    )}
                    {p.last_test_ok && (
                      <span className="badge ghost-success" style={{ marginLeft: '0.5rem' }}>
                        ✓ Tested
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button size="sm" bracket onClick={() => testProvider(p.id)}>
                    {testStatus.loading ? 'Testing...' : 'Test'}
                  </Button>
                  <Button size="sm" bracket onClick={() => openModal(p)}>
                    Edit
                  </Button>
                  <Button size="sm" bracket variant="danger" onClick={() => setDeleteId(p.id)}>
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hd">
              <h3>{editingId ? 'Edit Provider' : 'Add OIDC Provider'}</h3>
              <button onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-bd stack stack-4">
              <div>
                <label className="label">Provider Name</label>
                <input
                  className="inp"
                  value={providerName}
                  onChange={(e) => setProviderName(e.target.value)}
                  placeholder="e.g., Keycloak Prod"
                />
              </div>

              <div>
                <label className="label">Quick Fill</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {Object.keys(PRESETS).map((key) => (
                    <Button key={key} size="sm" bracket onClick={() => applyPreset(key)}>
                      {key}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <label className="label">Issuer URL</label>
                <input
                  className="inp"
                  value={formData.issuer}
                  onChange={(e) => setFormData({ ...formData, issuer: e.target.value })}
                  placeholder="https://keycloak.example.com/realms/finna"
                />
              </div>

              <div>
                <label className="label">Client ID</label>
                <input
                  className="inp"
                  value={formData.client_id}
                  onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                  placeholder="finna-app"
                />
              </div>

              <div>
                <label className="label">Client Secret</label>
                <input
                  className="inp"
                  type="password"
                  value={formData.client_secret}
                  onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                  placeholder={editingId ? '(leave blank to keep existing)' : ''}
                />
              </div>

              <div>
                <label className="label">Redirect URI</label>
                <input className="inp" value={formData.redirect_uri} disabled />
                <div className="mono muted" style={{ fontSize: 10, marginTop: '0.25rem' }}>
                  Auto-populated from current origin. Copy this for IdP setup.
                </div>
              </div>

              <div>
                <label>
                  <input
                    type="checkbox"
                    checked={formData.auto_provision}
                    onChange={(e) => setFormData({ ...formData, auto_provision: e.target.checked })}
                  />
                  Auto-provision users on first login
                </label>
              </div>

              <div>
                <label className="label">Allowed Email Domains (comma-separated)</label>
                <input
                  className="inp"
                  value={formData.allowed_email_domains.join(', ')}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      allowed_email_domains: e.target.value.split(',').map((d) => d.trim()),
                    })
                  }
                  placeholder="example.com, acme.co"
                />
              </div>
            </div>
            <div className="modal-ft">
              <Button bracket onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" bracket onClick={saveProvider}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Provider"
        message="Are you sure? Users linked to this provider will need reassignment."
        onConfirm={deleteProvider}
        variant="danger"
      />
    </div>
  )
}
