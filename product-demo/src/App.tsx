import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { Editors, Page, Workspace } from './domain/types'
import { initialWorkspace } from './services/workspace'
import { installWingCatalog } from './services/wingCatalog'
import Icon from './components/Icon'
import SourcesPage from './pages/SourcesPage'
import AgentPage from './pages/AgentPage'

const ModelingPage = lazy(() => import('./pages/ModelingPage'))
const STORAGE = 'sgtrace-lightweight-v1'
const navigation: { id: Page; title: string; icon: 'source' | 'model' | 'agent' }[] = [
  { id: 'sources', title: '数据源接入', icon: 'source' },
  { id: 'modeling', title: '本体建模', icon: 'model' },
  { id: 'agent', title: '字段溯源智能体', icon: 'agent' },
]
function pageForPath(): Page {
  const path = window.location.pathname
  if (path.startsWith('/sources') || path.includes('materials') || path.includes('connections')) return 'sources'
  if (path.startsWith('/modeling') || path.startsWith('/knowledge')) return 'modeling'
  return 'agent'
}

export default function App() {
  const [page, setPage] = useState<Page>(pageForPath)
  const [storageIssue, setStorageIssue] = useState('')
  const [state, setState] = useState<Workspace>(() => {
    try {
      const value = localStorage.getItem(STORAGE)
      if (value) {
        const data = JSON.parse(value)
        if (Array.isArray(data.sources) && data.editors?.model && data.active?.editors && Array.isArray(data.turns)) return data
      }
    } catch { /* 损坏的缓存不影响打开页面，下次保存会写入可用状态。 */ }
    return initialWorkspace()
  })
  const latest = useRef(state)
  latest.current = state
  useEffect(() => installWingCatalog(() => latest.current), [])
  useEffect(() => {
    try { localStorage.setItem(STORAGE, JSON.stringify(state)); setStorageIssue('') }
    catch { setStorageIssue('浏览器存储不可用，当前操作只能在本次页面内保留。') }
  }, [state])
  useEffect(() => {
    const pop = () => setPage(pageForPath())
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])
  const go = (next: Page) => { history.pushState(null, '', `/${next}`); setPage(next); window.scrollTo(0, 0) }
  const edit = (editors: Editors) => setState(current => ({ ...current, editors, revision: current.revision === current.active.revision ? current.revision + 1 : current.revision }))
  return <div className="light-product">
    <header className="product-header">
      <a href="/agent" className="product-name" onClick={e => { e.preventDefault(); go('agent') }}><span className="product-symbol"><Icon name="model" /></span><strong>字段溯源</strong><span className="domain-label">营销域</span></a>
      <nav className="primary-navigation" aria-label="产品功能">{navigation.map((item, index) => <button key={item.id} type="button" aria-current={page === item.id ? 'page' : undefined} onClick={() => go(item.id)}><span className="nav-number">0{index + 1}</span><Icon name={item.icon} />{item.title}</button>)}</nav>
      <span className="prototype-tag">交互原型</span>
    </header>
    <main className={`product-body ${page === 'modeling' ? 'wide-body' : ''}`}>
      {storageIssue && <p className="inline-note" role="alert">{storageIssue}</p>}
      {page === 'sources' && <SourcesPage state={state} onChange={setState} onNavigate={go} />}
      {page === 'modeling' && <Suspense fallback={<p role="status" className="loading">正在载入 OntoWing 编辑器…</p>}><ModelingPage state={state} onEdit={edit} onChange={setState} onNavigate={go} /></Suspense>}
      {page === 'agent' && <AgentPage state={state} onChange={setState} onNavigate={go} />}
    </main>
    <footer className="product-footer"><span>数据源 <span>→</span> OntoWing 本体 + R2RML <span>→</span> 字段溯源</span><span>本地模拟数据 · 所有功能统一使用</span></footer>
  </div>
}
