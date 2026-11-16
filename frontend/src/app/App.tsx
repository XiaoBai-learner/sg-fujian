import { useEffect, useState } from 'react'
import SourcesPage from '../modules/sources'
import ModelingPage from '../modules/modeling'
import AgentPage from '../modules/agent'
import { checkHealth } from '../shared/api/client'

const pages = [
  { path: '/agent', title: '字段溯源', Component: AgentPage },
  { path: '/sources', title: '数据源接入', Component: SourcesPage },
  { path: '/modeling', title: '本体建模', Component: ModelingPage },
]

export default function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [health, setHealth] = useState<'pending' | 'ok' | 'unavailable'>('pending')
  useEffect(() => {
    const controller = new AbortController()
    void checkHealth(controller.signal).then(available => {
      if (!controller.signal.aborted) setHealth(available ? 'ok' : 'unavailable')
    }).catch(() => { if (!controller.signal.aborted) setHealth('unavailable') })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    const pop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])
  const page = pages.find(page => page.path === path) ?? pages[0]
  const Page = page.Component
  return <div className="workspace">
    <aside>
      <a className="brand" href="/agent" onClick={event => { event.preventDefault(); history.pushState(null, '', '/agent'); setPath('/agent') }}>溯源<span>WORKSPACE</span></a>
      <nav aria-label="产品模块">{pages.map(item => <a key={item.path} href={item.path} aria-current={page.path === item.path ? 'page' : undefined} onClick={event => {
        event.preventDefault(); history.pushState(null, '', item.path); setPath(item.path)
      }}>{item.title}</a>)}</nav>
      <span className="domain">营销域工作区</span>
    </aside>
    <div className="content">
      <header><span>{page.title}</span><span className={`service-state ${health}`} role="status">{health === 'pending' ? '正在连接服务' : health === 'ok' ? '服务可用' : '服务未连接'}</span></header>
      <main><Page /></main>
    </div>
  </div>
}
