import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import SourcesPage from '../modules/sources'
import ModelingPage from '../modules/modeling'
import AgentPage, { type Turn } from '../modules/agent'
import { checkHealth } from '../shared/api/client'
import Icon, { type IconName } from '../shared/Icon'
import useModelingWorkspace from '../modules/modeling/useModelingWorkspace'
import AccountsPage from '../modules/accounts'
import { api, type Account } from '../shared/api/session'

const pages: { path: string; title: string; icon: IconName }[] = [
  { path: '/sources', title: '数据源接入', icon: 'source' },
  { path: '/modeling', title: '本体建模', icon: 'model' },
]

export default function App({ user, onLogout }: { user: Account; onLogout: () => void }) {
  const [path, setPath] = useState(window.location.pathname)
  const {state, dispatch, busy, generate, reload} = useModelingWorkspace()
  const [health, setHealth] = useState<'pending' | 'ok' | 'unavailable'>('pending')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [about, setAbout] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [turnId, setTurnId] = useState<string | null>(null)
  const aboutDialog = useRef<HTMLDialogElement>(null)
  const sidebar = useRef<HTMLElement>(null)
  const content = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    void checkHealth(controller.signal).then(available => {
      if (!controller.signal.aborted) setHealth(available ? 'ok' : 'unavailable')
    }).catch(() => { if (!controller.signal.aborted) setHealth('unavailable') })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    const pop = () => { setPath(window.location.pathname); setMobileOpen(false) }
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])
  useEffect(() => {
    if (about) aboutDialog.current?.showModal()
    else aboutDialog.current?.close()
  }, [about])
  useEffect(() => {
    if (!mobileOpen) return
    const previous = document.activeElement as HTMLElement | null
    content.current?.setAttribute('inert', '')
    sidebar.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileOpen(false)
      if (event.key !== 'Tab') return
      const controls = [...sidebar.current!.querySelectorAll<HTMLElement>('a, button')].filter(item => item.offsetParent !== null)
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus() }
      if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus() }
    }
    const media = window.matchMedia('(max-width: 760px)')
    const resize = () => { if (!media.matches) setMobileOpen(false) }
    window.addEventListener('keydown', keydown)
    media.addEventListener('change', resize)
    return () => { content.current?.removeAttribute('inert'); window.removeEventListener('keydown', keydown); media.removeEventListener('change', resize); previous?.focus() }
  }, [mobileOpen])
  const go = (next: string) => { history.pushState(null, '', next); setPath(next); setMobileOpen(false) }
  const newTrace = () => { setTurnId(null); go('/agent') }
  const title = path === '/accounts' ? '账户管理' : pages.find(item => item.path === path)?.title ?? '字段溯源'
  useLayoutEffect(() => { window.scrollTo(0, 0) }, [path, turnId])
  return <div className={`workspace ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
    <a className="skip-link" href="#main-content">跳到工作区</a>
    {mobileOpen && <button className="sidebar-scrim" aria-label="关闭导航" onClick={() => setMobileOpen(false)} />}
    <aside ref={sidebar} className="sidebar" aria-label="工作台导航" role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen || undefined}>
      <div className="sidebar-brand"><a className="brand" href="/agent" onClick={event => { event.preventDefault(); newTrace() }} aria-label="字段溯源首页">
        <span className="brand-symbol"><Icon name="trace" size={25} /></span><strong>溯源</strong><span className="brand-label">WORKSPACE</span></a>
        <button className="icon-button collapse-control" aria-label="收起侧栏" onClick={() => { setCollapsed(true); setMobileOpen(false) }}><Icon name="panel" size={18} /></button></div>
      <button className="new-trace" onClick={newTrace} title="新建溯源"><Icon name="plus" /><span>新建溯源</span><span>↗</span></button>
      <nav className="module-nav" aria-label="产品模块">{pages.map(item => <a key={item.path} href={item.path}
        title={item.title} aria-current={path === item.path ? 'page' : undefined} onClick={event => { event.preventDefault(); go(item.path) }}>
        <Icon name={item.icon} /><span>{item.title}</span>{item.path === '/modeling' && <small>OntoWing</small>}</a>)}</nav>
      <div className="sidebar-history"><div className="sidebar-section">工作区</div>
        <div className="workspace-folder"><Icon name="folder" size={18} /><span>营销域工作区</span></div>
        <nav aria-label="溯源记录">{path !== '/sources' && path !== '/modeling' && !turnId && <button className="active" onClick={newTrace}>新溯源<span className="live-dot" /></button>}
          {[...turns].reverse().map(turn => <button key={turn.id} className={turn.id === turnId && title === '字段溯源' ? 'active' : ''} onClick={() => { setTurnId(turn.id); go('/agent') }}>{turn.question}</button>)}
        </nav>{!turns.length && <p>每一次溯源，都有迹可循</p>}
      </div>
      <div className="sidebar-bottom"><span className="workspace-avatar">{user.display_name.slice(0, 1)}</span>
        <div><strong>{user.display_name}</strong><button className="text-button" onClick={() => go('/accounts')}>账户管理</button></div>
        <button className="icon-button" aria-label="退出登录" title="退出登录" onClick={async () => {
          try { await api('auth/logout', {}); onLogout() } catch { window.alert('退出失败，请重试') }
        }}><Icon name="logout" size={18} /></button></div>
    </aside>
    <div ref={content} className="content">
      <header className="topbar"><div><button className="icon-button expand-control" aria-label="展开侧栏"
        onClick={() => { setCollapsed(false); setMobileOpen(window.matchMedia('(max-width: 760px)').matches) }}><Icon name="panel" size={18} /></button>
        <span>营销域工作区</span><Icon name="chevron" size={14} /><strong>{title}</strong></div>
        <button className="product-status" onClick={() => setAbout(true)}><span />关于工作台</button>
      </header>
      <main id="main-content" aria-busy={!!busy} tabIndex={-1} className={`page-body ${title === '字段溯源' ? 'agent-body' : ''}`}>
        {busy && <p className="message info" role="status">{busy}</p>}
        <fieldset disabled={!!busy} className="workspace-controls">
        {path === '/accounts' ? <AccountsPage user={user} onLogout={onLogout} /> :
          path === '/sources' ? <SourcesPage state={state} dispatch={dispatch} onModel={() => go('/modeling')} /> :
          path === '/modeling' ? <ModelingPage state={state} dispatch={dispatch} onTrace={newTrace} onGenerate={generate} onReload={reload} /> :
            <AgentPage active={state.active} turn={turns.find(turn => turn.id === turnId)} onModel={() => go('/modeling')}
              onTurn={turn => { setTurns(current => [...current, turn]); setTurnId(turn.id) }} />}
        </fieldset>
      </main>
    </div>
    <dialog ref={aboutDialog} className="about-dialog" onCancel={() => setAbout(false)} onClose={() => setAbout(false)} aria-labelledby="about-title">
      <div className="section-heading"><h2 id="about-title">字段溯源工作台</h2><button className="icon-button" aria-label="关闭" onClick={() => setAbout(false)}><Icon name="close" /></button></div>
      <p>当前版本支持真实 DDL / SQL 建模、服务端草稿、OntoWing 静态校验与导出、采用快照和字段溯源。</p>
      <p>上传的文本材料保存到后端后参与结构解析。可选语义增强会把所选材料发送到部署配置的模型服务；表字段候选由解析器约束。</p>
      <p>PDF 正文解析、映射实跑与真实数据集效果评测仍待接入；静态校验通过不代表业务语义已被证明。</p>
      <p className="service-state">{health === 'pending' ? '后端存活检查中' : health === 'ok' ? '后端进程可达' : '后端连接不可用，请恢复连接后继续操作'}</p>
      <button className="button primary" onClick={() => setAbout(false)}>知道了</button>
    </dialog>
  </div>
}
