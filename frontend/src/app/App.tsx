import { useEffect, useState } from 'react'
import SourcesPage from '../modules/sources'
import MaterialsPage from '../modules/sources/MaterialsPage'
import ModelingPage, {type StudioSection} from '../modules/modeling'
import ModelCatalog from '../modules/modeling/ModelCatalog'
import { modelIdFromPath } from '../modules/modeling/catalog'
import AgentPage, { type Turn } from '../modules/agent'
import Icon from '../shared/Icon'
import AccountsPage from '../modules/accounts'
import { api, type Account } from '../shared/api/session'

export default function App({ user, onLogout }: { user: Account; onLogout: () => void }) {
  const [path, setPath] = useState(window.location.pathname)
  const [turns, setTurns] = useState<Turn[]>([])
  const [turnId, setTurnId] = useState<string | null>(null)
  const [modelSection,setModelSection]=useState<StudioSection>('ontology')
  const [traceModel, setTraceModel] = useState<string | null>(null)
  const modelId = modelIdFromPath(path)
  const activePath = modelId ? '/modeling' : path === '/' ? '/agent' : path
  const title = activePath === '/accounts' ? '账户管理' : activePath === '/modeling' ? '本体模型' : activePath === '/sources' ? '数据库连接' : activePath === '/materials' ? '文档材料' : '溯源问答'
  useEffect(() => { const pop = () => setPath(window.location.pathname); window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop) }, [])
  const go = (next: string) => { history.pushState(null, '', next); setPath(next) }
  const newTrace = () => { setTurnId(null); go('/agent') }
  const link = (target: string, label: string, icon: 'source' | 'file' | 'model' | 'agent') => <a href={target} aria-current={activePath === target ? 'page' : undefined} onClick={event => { event.preventDefault(); go(target) }}><Icon name={icon} size={16} />{label}</a>
  return <div className="product-app unified-app">
    <a className="skip-link" href="#main-content">跳到工作区</a>
    <header className="product-header"><a className="product-brand" href="/modeling" onClick={event => { event.preventDefault(); go('/modeling') }} aria-label="字段溯源工作台"><span><Icon name="model" size={19} /></span><strong>溯源工作台</strong></a><span className="header-workspace">工作台</span><div className="product-account"><details className="account-menu"><summary><span className="account-initial">{user.display_name.slice(0, 1)}</span><span>{user.display_name}</span><Icon name="down" size={12} /></summary><div><button onClick={() => go('/accounts')}><Icon name="settings" size={15} />账户管理</button><button onClick={async () => { try { await api('auth/logout', {}); onLogout() } catch { window.alert('退出失败，请重试') } }}><Icon name="logout" size={15} />退出登录</button></div></details></div></header>
    <div className="product-layout"><aside className="context-sidebar unified-sidebar" aria-label="工作台功能菜单"><div className="context-caption">数据源接入</div><nav className="context-links" aria-label="数据源接入">{link('/sources', '数据库连接', 'source')}{link('/materials', '文档材料', 'file')}</nav><div className="context-caption section-gap">本体建模</div><nav className="context-links" aria-label="本体建模">{link('/modeling', '本体模型', 'model')}{modelId&&<div className="model-function-links">{([['materials','file','材料选择'],['ontology','model','本体画布'],['validation','shield','校验与采用']] as const).map(([value,icon,label])=><button key={value} aria-current={modelSection===value?'page':undefined} onClick={()=>setModelSection(value)}><Icon name={icon} size={15}/>{label}</button>)}</div>}</nav><div className="context-caption section-gap">字段溯源</div><nav className="context-links">{link('/agent', '溯源问答', 'agent')}</nav>{activePath === '/agent' && <><button className="button secondary context-new-chat" onClick={newTrace}><Icon name="plus" size={15} />新建问答</button><nav className="context-links conversation-links" aria-label="最近问答">{[...turns].reverse().map(turn => <button key={turn.id} aria-current={turn.id === turnId ? 'page' : undefined} onClick={() => { setTurnId(turn.id); go('/agent') }}><Icon name="agent" size={14} /><span>{turn.question}</span></button>)}</nav></>}<div className="context-footer"><Icon name="shield" size={14} /><span>字段来源 · 有据可查</span></div></aside>
      {modelId ? <main id="main-content" tabIndex={-1} className="product-model-main"><ModelingPage key={modelId} id={modelId} section={modelSection} setSection={setModelSection} onBack={() => go('/modeling')} onSources={() => go('/materials')} onTrace={() => { setTraceModel(modelId); newTrace() }} /></main> : <div className="product-page-content"><main id="main-content" tabIndex={-1} aria-label={title} className={`page-body ${activePath === '/agent' ? 'agent-body' : ''}`}>
        {activePath === '/accounts' ? <AccountsPage user={user} onLogout={onLogout} /> : activePath === '/sources' ? <SourcesPage onMaterials={() => go('/materials')} /> : activePath === '/materials' ? <MaterialsPage /> : activePath === '/modeling' ? <ModelCatalog navigate={go} /> : <AgentPage key={`agent-${traceModel ?? ''}`} initialModelId={traceModel} turn={turns.find(turn => turn.id === turnId)} onModel={() => go('/modeling')} onTurn={turn => { setTurns(current => [...current, turn]); setTurnId(turn.id) }} />}
      </main></div>}
    </div>
  </div>
}
