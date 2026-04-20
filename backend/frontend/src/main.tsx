import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { createRoot } from 'react-dom/client'

// Simple page components
const Dashboard = () => <div><h2>Dashboard</h2><p>Cost overview coming soon...</p></div>
const Costs = () => <div><h2>Cost Explorer</h2><p>Get started by adding cloud providers</p></div>
const Alerts = () => <div><h2>Alerts</h2><p>No alerts configured yet</p></div>
const Config = () => <div><h2>Configuration</h2><p>Add your cloud provider connections</p></div>

const Login = () => {
  const [username, setUsername] = React.useState('admin')
  const [password, setPassword] = React.useState('')
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // For now, just navigate to dashboard
    window.location.href = '/dashboard'
  }
  
  return (
    <div style={{ maxWidth: '400px', margin: '100px auto' }}>
      <h2>FinOps Console Login</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label>Username:</label>
          <input type="text" value={username} onChange={e => setUsername(e.target.value)} style={{ width: '100%', padding: '8px', marginLeft: '10px' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Password:</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={{ width: '100%', padding: '8px', marginLeft: '10px' }} />
        </div>
        <button type="submit" style={{ padding: '10px 20px', cursor: 'pointer' }}>Login</button>
      </form>
      <p style={{ marginTop: '20px', color: '#888' }}>Default: admin / (any password)</p>
    </div>
  )
}

const Root = () => {
  const [authenticated, setAuthenticated] = React.useState(false)
  
  React.useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('finops_token')
    if (token) {
      setAuthenticated(true)
    }
  }, [])
  
  if (!authenticated) {
    return <Login />
  }
  
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <nav style={{ width: '200px', backgroundColor: '#1a1a2e', padding: '20px', color: 'white' }}>
          <h2>FinOps</h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ margin: '10px 0' }}><a href="/dashboard" style={{ color: 'white', textDecoration: 'none' }}>Dashboard</a></li>
            <li style={{ margin: '10px 0' }}><a href="/costs" style={{ color: 'white', textDecoration: 'none' }}>Costs</a></li>
            <li style={{ margin: '10px 0' }}><a href="/alerts" style={{ color: 'white', textDecoration: 'none' }}>Alerts</a></li>
            <li style={{ margin: '10px 0' }}><a href="/config" style={{ color: 'white', textDecoration: 'none' }}>Config</a></li>
          </ul>
        </nav>
        <main style={{ flex: 1, padding: '20px' }}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/costs" element={<Costs />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/config" element={<Config />} />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default Root

// Mount the React app
const root = createRoot(document.getElementById('root')!)
root.render(<Root />)
