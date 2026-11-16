import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { Editors, Page, Workspace } from './domain/types'
import { initialWorkspace } from './services/workspace'
import { installWingCatalog } from './services/wingCatalog'
import Icon from './components/Icon'
import Dialog from './components/Dialog'
import SourcesPage from './pages/SourcesPage'
import AgentPage from './pages/AgentPage'

const ModelingPage = lazy(() => import('./pages/ModelingPage'))
const STORAGE = 'sgtrace-lightweight-v1'
const navigation: { id: Page; title: string; icon: 'source' | 'model' | 'agent' }[] = [
  { id: 'sources', title: '数据源接入', icon: 'source' },
  { id: 'modeling', title: '本体建模', icon: 'model' },
]
function pageForPath(): Page {
  const path = window.location.pathname
  if (path.startsWith('/sources') || path.includes('materials') || path.includes('connections')) return 'sources'
  if (path.startsWith('/modeling') || path.startsWith('/knowledge')) return 'modeling'
  return 'agent'
}

export default function App() {
  const [page, setPage] = useState<Page>(pageForPath)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebar, setMobileSidebar] = useState(false)
  const [showAbout, setShowAbout] = useState(false)
  const [searchHistory, setSearchHistory] = useState(false)
  const [historyQuery, setHistoryQuery] = useState('')
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null)
  const [newTraceId, setNewTraceId] = useState(0)
  const sidebar = useRef<HTMLElement>(null)
  const main = useRef<HTMLDivElement>(null)
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
  const go = (next: Page) => { history.pushState(null, '', `/${next}`); setPage(next); setMobileSidebar(false) }
  const newTrace = () => { setActiveTurnId(null); setNewTraceId(value => value + 1); go('agent') }
  useEffect(() => {
    if (!mobileSidebar) return
    const previousFocus = document.activeElement as HTMLElement | null
    const content = main.current
    content?.setAttribute('inert', '')
    sidebar.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const media = window.matchMedia('(max-width: 760px)')
    const resize = () => { if (!media.matches) setMobileSidebar(false) }
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileSidebar(false)
      if (event.key !== 'Tab') return
      const items = [...(sidebar.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input') || [])].filter(item => item.offsetParent !== null)
      const first = items[0], last = items.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    window.addEventListener('keydown', keydown)
    media.addEventListener('change', resize)
    return () => {
      window.removeEventListener('keydown', keydown)
      media.removeEventListener('change', resize)
      content?.removeAttribute('inert')
      previousFocus?.focus()
    }
  }, [mobileSidebar])
  const edit = (editors: Editors) => setState(current => ({ ...current, editors, revision: current.revision === current.active.revision ? current.revision + 1 : current.revision }))
  const turns = [...state.turns].reverse().filter(turn => turn.question.toLowerCase().includes(historyQuery.toLowerCase()))
  return <div className={`trace-workbench${sidebarCollapsed ? ' sidebar-collapsed' : ''}${mobileSidebar ? ' mobile-sidebar-open' : ''}`}>
    <a className="skip-link" href="#workspace-content">跳到工作区</a>
    {mobileSidebar && <button className="sidebar-scrim" aria-label="关闭导航" onClick={() => setMobileSidebar(false)} />}
    <aside ref={sidebar} className="workspace-sidebar" aria-label="工作台导航" role={mobileSidebar ? 'dialog' : undefined} aria-modal={mobileSidebar || undefined}>
      <div className="sidebar-brand">
        <a href="/agent" className="product-name" aria-label="字段溯源首页" onClick={e => { e.preventDefault(); newTrace() }}><Icon name="trace" /><strong>溯源</strong><span>WORKSPACE</span></a>
        <button className="icon-button sidebar-toggle" title="收起侧栏" aria-label="收起侧栏" onClick={() => { setSidebarCollapsed(true); setMobileSidebar(false) }}><Icon name="panel" /></button>
      </div>
      <button className={`new-trace${page === 'agent' && !activeTurnId ? ' is-current' : ''}`} aria-label="新建溯源" title="新建溯源" onClick={newTrace}><Icon name="plus" /><span>新建溯源</span><span className="new-trace-mark">↗</span></button>
      <nav className="workspace-navigation" aria-label="数据与本体">{navigation.map(item => <button key={item.id} type="button" title={item.title} aria-label={item.title} aria-current={page === item.id ? 'page' : undefined} onClick={() => go(item.id)}><Icon name={item.icon} /><span>{item.title}</span>{item.id === 'modeling' && <small>OntoWing</small>}</button>)}</nav>
      <div className="sidebar-history">
        <div className="sidebar-section-label"><span>工作区</span><button className="icon-button" title="搜索溯源记录" aria-label="搜索溯源记录" aria-expanded={searchHistory} onClick={() => { setSearchHistory(!searchHistory); setHistoryQuery('') }}><Icon name="search" /></button></div>
        {searchHistory && <label className="history-search"><span className="sr-only">搜索溯源记录</span><input autoFocus placeholder="搜索溯源记录" value={historyQuery} onChange={e => setHistoryQuery(e.target.value)} /></label>}
        <div className="workspace-folder"><Icon name="folder" /><span>营销域工作区</span><small>{state.turns.length || ''}</small></div>
        <nav className="history-items" aria-label="溯源记录">
          {page === 'agent' && !activeTurnId && <button className="is-active" onClick={newTrace}><span>新溯源</span><i /></button>}
          {turns.map(turn => <button key={turn.id} className={page === 'agent' && activeTurnId === turn.id ? 'is-active' : ''} title={turn.question} onClick={() => { setActiveTurnId(turn.id); go('agent') }}><span>{turn.question}</span></button>)}
          {!turns.length && <p className="history-empty">{historyQuery ? '没有匹配的记录' : '提问后，记录会保留在这里'}</p>}
        </nav>
      </div>
      <div className="sidebar-bottom"><span className="workspace-avatar">营</span><div><strong>营销域</strong><span>我的工作区</span></div><button className="icon-button" title="关于此工作台" aria-label="关于此工作台" onClick={() => setShowAbout(true)}><Icon name="help" /></button></div>
    </aside>
    <div ref={main} className="workspace-main">
      <header className="workspace-topbar">
        <button className="icon-button expand-sidebar" aria-label="展开侧栏" title="展开侧栏" aria-expanded={mobileSidebar} onClick={() => { setSidebarCollapsed(false); setMobileSidebar(window.matchMedia('(max-width: 760px)').matches) }}><Icon name="panel" /></button>
        <div className="workspace-breadcrumb"><span>营销域工作区</span><Icon name="chevron" /><strong>{page === 'agent' ? '字段溯源' : page === 'sources' ? '数据源接入' : '本体建模'}</strong></div>
        <button className="preview-label" onClick={() => setShowAbout(true)}>预览版</button>
      </header>
      {storageIssue && <p className="storage-note" role="alert">{storageIssue}</p>}
      <main id="workspace-content" tabIndex={-1} className={`product-body ${page === 'modeling' ? 'wide-body' : page === 'agent' ? 'agent-body' : ''}`}>
        {page === 'sources' && <SourcesPage state={state} onChange={setState} onNavigate={go} />}
        {page === 'modeling' && <Suspense fallback={<p role="status" className="loading">正在载入 OntoWing 编辑器…</p>}><ModelingPage state={state} onEdit={edit} onChange={setState} onNavigate={go} /></Suspense>}
        {page === 'agent' && <AgentPage key={activeTurnId ?? `new-${newTraceId}`} state={state} activeTurnId={activeTurnId} onSelectTurn={setActiveTurnId} onChange={setState} onNavigate={go} />}
      </main>
    </div>
    {showAbout && <Dialog titleId="about-title" onClose={() => setShowAbout(false)}><div className="dialog-heading"><div><h2 id="about-title">字段溯源工作台</h2><p>数据接入 · OntoWing 建模 · 字段溯源</p></div><button className="icon-button" aria-label="关闭" onClick={() => setShowAbout(false)}><Icon name="close" /></button></div><div className="about-copy"><p>每个人都可以接入数据、维护本体和发起溯源，使用同一套功能。</p><p>当前是交互预览版。连接配置、材料正文、模型编辑和溯源记录保存在本机浏览器，查询使用本地模型快照模拟。</p><p>尚未连接真实数据库、OntoWing 后端或大模型。文本和基本 DDL 支持本地草稿预览，PDF 等待后端解析，数据库口令不会保存。</p><p><a href="/architecture.html" target="_blank" rel="noreferrer">查看三层产品架构图 ↗</a></p></div><div className="dialog-actions"><button className="action primary" onClick={() => setShowAbout(false)}>知道了</button></div></Dialog>}
  </div>
}
