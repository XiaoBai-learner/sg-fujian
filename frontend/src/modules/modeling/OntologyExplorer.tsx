import { useCallback, useEffect, useRef, useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import OntologyGraph, { type OntologySelection } from './OntologyGraph'
import OntologyInspector from './OntologyInspector'
import { workspaceReducer, type WorkspaceAction, type WorkspaceState } from './state'
import './ontology.css'

export default function OntologyExplorer({ state, dispatch }: { state: WorkspaceState; dispatch: Dispatch<WorkspaceAction> }) {
  const [selected, setSelected] = useState<OntologySelection>({ kind: 'class', id: state.draft?.classes[0]?.id ?? '' })
  const [dirty, setDirty] = useState(false)
  const [pending, setPending] = useState<OntologySelection | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [fullscreen, setFullscreen] = useState(false)
  const root = useRef<HTMLElement>(null)
  const previousSelection = useRef(selected)
  const onDirty = useCallback((value: boolean) => setDirty(value), [])
  useEffect(() => {
    const changed = () => setFullscreen(document.fullscreenElement === root.current)
    document.addEventListener('fullscreenchange', changed)
    return () => document.removeEventListener('fullscreenchange', changed)
  }, [])
  useEffect(() => {
    if (previousSelection.current === selected) return
    previousSelection.current = selected
    if (window.matchMedia('(max-width: 1024px)').matches) root.current?.querySelector('.ontology-inspector')?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start',
    })
  }, [selected])
  useEffect(() => {
    if (!dirty && pending) { setSelected(pending); setPending(null) }
  }, [dirty, pending])
  if (!state.draft) return null
  const draft = state.draft
  const select = (value: OntologySelection) => {
    if (value.id === selected.id && value.kind === selected.kind) return
    if (dirty) { setPending(value); return }
    setSelected(value); setPending(null)
  }
  const save = (action: WorkspaceAction) => {
    const next = workspaceReducer(state, action)
    if (next.error) return next.error
    dispatch(action)
    return null
  }
  const catalog = [
    ...draft.classes.map(item => ({ ...item, kind: 'class' as const, label: '类' })),
    ...draft.relations.map(item => ({ ...item, kind: 'relation' as const, label: '关系' })),
    ...draft.items.map(item => ({ ...item, kind: 'property' as const, label: '属性' })),
  ].filter(item => `${item.name} ${item.id}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()))
  return <section className="ontology-explorer" ref={root} aria-label="完整本体编辑工作台">
    <div className="ontology-explorer-heading"><div><h3>完整本体</h3><p>{draft.classes.length} 个类 · {draft.items.length} 个属性 · {draft.relations.length} 条关系 <span>草稿 r{draft.revision}</span></p></div>
      <button className="button secondary" onClick={async () => {
        try {
          if (document.fullscreenElement) await document.exitFullscreen()
          else await root.current?.requestFullscreen()
        } catch { setError('浏览器不支持全屏，请使用画布缩放和侧栏收起功能。') }
      }}><Icon name="expand" size={16} />{fullscreen ? '退出全屏' : '全屏查看'}</button></div>
    {error && <p className="message error" role="alert">{error}</p>}
    <details className="ontology-catalog" open={!!query || undefined}>
      <summary><Icon name="search" size={15} />对象目录 · 搜索并定位类、属性或关系</summary>
      <label className="visually-hidden" htmlFor="ontology-search">搜索本体对象</label>
      <input id="ontology-search" placeholder="按名称或标识搜索" value={query} onChange={event => setQuery(event.target.value)} />
      <div>{catalog.map(item => <button key={`${item.kind}:${item.id}`} onClick={() => select({ kind: item.kind, id: item.id })}
        aria-pressed={selected.kind === item.kind && selected.id === item.id}><small>{item.label}</small>{item.name}</button>)}
        {!catalog.length && <p>没有匹配对象。清空搜索可查看完整目录。</p>}</div>
    </details>
    {pending && <div className="unsaved-selection" role="alert"><Icon name="info" size={18} /><span>当前详情有未保存修改。请先保存，或放弃本次修改后切换。</span>
      <button className="button secondary" onClick={() => { setDirty(false); setSelected(pending); setPending(null) }}>放弃修改并切换</button>
      <button className="text-button" onClick={() => setPending(null)}>继续编辑</button></div>}
    <div className="ontology-editor-layout">
      <OntologyGraph draft={draft} selected={selected} onSelect={select} />
      <OntologyInspector key={`${selected.kind}:${selected.id}`} draft={draft} selection={selected}
        materials={state.materials} onSave={save} onDirty={onDirty} />
    </div>
    <p className="ontology-editor-note"><Icon name="shield" size={15} />全部对象来自当前草稿，待确认属性和关系也会显示。保存后重新检查，再采用为溯源版本。修改由服务端保存。</p>
  </section>
}
