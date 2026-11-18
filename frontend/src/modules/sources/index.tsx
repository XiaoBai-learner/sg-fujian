import { useEffect, useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import { MaterialInput } from '../modeling/MaterialInput'
import type { WorkspaceAction, WorkspaceState } from '../modeling/state'
import { apiFetch } from '../../shared/api/session'

type Source = { id: string; name: string; kind: string; database: string | null; status: string }
export default function SourcesPage({ state, dispatch, onModel }: {
  state: WorkspaceState; dispatch: Dispatch<WorkspaceAction>; onModel: () => void
}) {
  const [tab, setTab] = useState<'materials' | 'connections'>('materials')
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    if (tab !== 'connections') return
    const controller = new AbortController()
    setLoading(true); setError('')
    void apiFetch('/api/v1/sources', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('连接目录暂不可用。请确认正式后端与数据库已配置。')
      const data = await response.json()
      if (!Array.isArray(data.items)) throw new Error('连接目录格式不正确。')
      if (!controller.signal.aborted) setSources(data.items)
    }).catch(error => {
      if (!controller.signal.aborted) setError(error instanceof Error ? error.message : '读取连接目录失败。')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [tab, refresh])
  return <section>
    <div className="page-heading"><div><span className="eyebrow">数据源接入</span><h1>结构与资料，一个入口</h1><p>原始材料统一管理，建模时直接选用。</p></div>
      <button className="button secondary" onClick={onModel}>去本体建模<Icon name="arrow" size={17} /></button></div>
    <div className="page-tabs" aria-label="接入内容">
      <button aria-pressed={tab === 'materials'} onClick={() => setTab('materials')}><Icon name="file" size={17} />建模材料<span>{state.materials.length}</span></button>
      <button aria-pressed={tab === 'connections'} onClick={() => setTab('connections')}><Icon name="source" size={17} />数据库连接</button>
    </div>
    <div className="modeling-surface sources-surface">{tab === 'materials' ?
      <MaterialInput state={state} dispatch={dispatch} compact /> :
      <section className="connections-panel"><div className="section-heading"><h2>已接入的数据源</h2><button className="button secondary" onClick={() => setRefresh(value => value + 1)} disabled={loading}>刷新目录</button></div>
        <p>查看已接入的数据库连接及其当前状态。</p>
        {loading ? <p role="status" className="message info">正在读取连接目录…</p> : error ? <p role="alert" className="message error">{error}</p> :
          sources.length ? <div className="table-scroll"><table><thead><tr><th>连接名称</th><th>类型</th><th>数据库</th><th>后端状态</th></tr></thead><tbody>{sources.map(source =>
            <tr key={source.id}><td>{source.name}</td><td>{source.kind}</td><td><code>{source.database ?? '—'}</code></td><td>{source.status}</td></tr>)}</tbody></table></div> :
            <div className="material-empty"><Icon name="source" size={30} /><p>后端还没有连接记录</p><span>可以先使用 DDL 进入材料流程。</span></div>}
        <p className="small-note">结构快照到建模材料的选用接口尚未接通。此处不会自动连接、修改数据库或保存口令。</p>
      </section>}</div>
  </section>
}
