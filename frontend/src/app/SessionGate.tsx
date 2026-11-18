import { useEffect, useState } from 'react'
import App from './App'
import LoginPage from '../modules/accounts/LoginPage'
import { api, setSession, type LoginSession } from '../shared/api/session'

export default function SessionGate() {
  const [session, updateSession] = useState<LoginSession | null>(null)
  const [initialized, setInitialized] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let disposed = false
    const expired = () => { setSession(null); updateSession(null) }
    window.addEventListener('session-expired', expired)
    void (async () => {
      try {
        const status = await api<{initialized: boolean}>('auth/status')
        if (disposed) return
        setInitialized(status.initialized)
        if (status.initialized) {
          const value = await api<LoginSession>('auth/session').catch(() => null)
          if (!disposed) { setSession(value); updateSession(value) }
        }
      } catch { if (!disposed) setError('无法连接服务，请确认后端与数据库已启动。') }
      finally { if (!disposed) setLoading(false) }
    })()
    return () => { disposed = true; window.removeEventListener('session-expired', expired) }
  }, [])
  if (loading || error) return <main className="session-loading" role="status"><p>{error || '正在验证登录状态…'}</p>
    {error && <button className="button secondary" onClick={() => location.reload()}>重新连接</button>}</main>
  if (!session) return <LoginPage initialized={initialized} onLogin={value => {
    setSession(value); updateSession(value); setInitialized(true)
  }} />
  return <App user={session.user} onLogout={() => { setSession(null); updateSession(null) }} />
}
