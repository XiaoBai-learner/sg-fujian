import { useEffect, useState } from 'react'
import AppShell from './components/AppShell'
import { ErrorState, LoadingState } from './components/AsyncState'
import { availableUsers, getSession, setDemoUser } from './services/mockService'
import type { Session } from './domain/types'
import WorkbenchPage from './pages/WorkbenchPage'
import NewRequestPage from './pages/NewRequestPage'
import RequestDetailPage from './pages/RequestDetailPage'
import KnowledgeOverviewPage from './pages/KnowledgeOverviewPage'
import MaterialsPage from './pages/MaterialsPage'
import KnowledgeModelPage from './pages/KnowledgeModelPage'
import ValidationPage from './pages/ValidationPage'
import VersionsPage from './pages/VersionsPage'
import ConnectionsPage from './pages/ConnectionsPage'
import AuditPage from './pages/AuditPage'

const users = availableUsers()

function currentPath() {
  return window.location.pathname || '/workbench'
}

export default function App() {
  const [session, setSession] = useState<Session>()
  const [path, setPath] = useState(currentPath())
  const [error, setError] = useState('')

  useEffect(() => {
    getSession().then(setSession).catch(e => setError(e instanceof Error ? e.message : '无法加载原型会话'))
    const onPop = () => setPath(currentPath())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = (next: string) => {
    if (next !== window.location.pathname) window.history.pushState({}, '', next)
    setPath(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const changeRole = (userId: string) => {
    setDemoUser(userId).then(next => {
      setSession(next)
      if (!['analyst', 'modeler', 'reviewer', 'admin'].includes(next.user.role)) navigate('/workbench')
    }).catch(e => setError(e instanceof Error ? e.message : '无法切换角色'))
  }

  if (error) return <ErrorState message={error} />
  if (!session) return <LoadingState label="正在加载产品原型…" />

  let page = <WorkbenchPage onNavigate={navigate} />
  if (path === '/requests/new') page = <NewRequestPage onNavigate={navigate} />
  else if (path.startsWith('/requests/')) page = <RequestDetailPage requestId={path.split('/')[2] || 'req-1206'} onNavigate={navigate} />
  else if (path === '/knowledge') page = <KnowledgeOverviewPage onNavigate={navigate} />
  else if (path === '/knowledge/materials') page = <MaterialsPage />
  else if (path === '/knowledge/model') page = <KnowledgeModelPage />
  else if (path === '/knowledge/validation') page = <ValidationPage onNavigate={navigate} />
  else if (path === '/knowledge/versions') page = <VersionsPage onNavigate={navigate} />
  else if (path === '/admin/connections') page = <ConnectionsPage />
  else if (path === '/admin/audit') page = <AuditPage />
  else if (path !== '/workbench') page = <div className="panel"><div className="empty-state"><strong>页面不存在</strong><p>这个原型路径还没有配置。</p><button className="btn primary" type="button" onClick={() => navigate('/workbench')}>回到工作台</button></div></div>

  return <AppShell session={session} users={users} activePath={path} onNavigate={navigate} onRoleChange={changeRole}>{page}</AppShell>
}
