import { useCallback, useEffect, useRef, useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import OntologyGraph, { type OntologySelection } from './OntologyGraph'
import OntologyInspector from './OntologyInspector'
import { workspaceReducer, type WorkspaceAction, type WorkspaceState } from './state'
import './ontology.css'

export default function OntologyExplorer({ state, dispatch, onEvidence }: { state: WorkspaceState; dispatch: Dispatch<WorkspaceAction>; onEvidence: () => void }) {
  const [selected, setSelected] = useState<OntologySelection>({ kind: 'class', id: '' })
  const [dirty, setDirty] = useState(false)
  const [query, setQuery] = useState('')
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [error, setError] = useState('')
  const [showProperties, setShowProperties] = useState(true)
  const [layoutKey, setLayoutKey] = useState(0)
  const [fullscreen, setFullscreen] = useState(false)
  const root = useRef<HTMLElement>(null)
  const editor = useRef<HTMLDialogElement>(null)
  const onDirty = useCallback((value: boolean) => setDirty(value), [])
  useEffect(() => {
    const changed = () => setFullscreen(document.fullscreenElement === root.current)
    document.addEventListener('fullscreenchange', changed)
    return () => document.removeEventListener('fullscreenchange', changed)
  }, [])
  useEffect(() => {
    if (selected.id) editor.current?.showModal()
    else editor.current?.close()
  }, [selected.id])
  if (!state.draft) return null
  const draft = state.draft
  const close = () => {
    if (dirty && !window.confirm('放弃尚未保存的修改？')) return
    setDirty(false); setSelected({ kind: 'class', id: '' })
  }
  const select = (value: OntologySelection) => {
    if (dirty && !window.confirm('放弃尚未保存的修改？')) return
    setDirty(false); setSelected(value); setCatalogOpen(false)
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
  return <section className="ontology-explorer canvas-first" ref={root} aria-label="完整本体编辑工作台">
    <div className="ontology-actionbar"><div className="ontology-search-control"><Icon name="search" size={14} /><input aria-label="查找本体对象" placeholder="查找类、属性或关系" value={query} onFocus={() => setCatalogOpen(true)} onChange={event => {setQuery(event.target.value);setCatalogOpen(true)}} onKeyDown={event => { if(event.key==='Escape') {setCatalogOpen(false);event.currentTarget.blur()} }} />{catalogOpen && <button aria-label="关闭对象搜索" className="icon-button" onClick={() => setCatalogOpen(false)}><Icon name="close" size={12} /></button>}</div>
      <span className="actionbar-divider" /><button className="canvas-action" onClick={() => setLayoutKey(value => value + 1)}><Icon name="fit" size={14} />重置布局</button><button className="canvas-action" aria-pressed={!showProperties} onClick={() => setShowProperties(!showProperties)}><Icon name="collapse" size={14} />{showProperties ? '收起属性' : '展开属性'}</button><button className="canvas-action" onClick={onEvidence}><Icon name="file" size={14} />字段依据</button><span className="actionbar-space" /><span className="canvas-read-hint">点击卡片或关系，编辑详情</span><button className="icon-button" title={fullscreen ? '退出全屏' : '全屏画布'} aria-label={fullscreen ? '退出全屏' : '全屏画布'} onClick={async () => {
        try { if (document.fullscreenElement) await document.exitFullscreen(); else await root.current?.requestFullscreen() }
        catch { setError('浏览器不支持全屏，请使用画布缩放。') }
      }}><Icon name="expand" size={15} /></button></div>
    {error && <p className="message error" role="alert">{error}</p>}
    {catalogOpen && <div className="canvas-catalog"><div className="catalog-result-heading">{query ? `搜索结果 · ${catalog.length}` : '本体对象'}</div><div>{catalog.map(item => <button key={`${item.kind}:${item.id}`} onClick={() => select({ kind: item.kind, id: item.id })}><small>{item.label}</small>{item.name}</button>)}{!catalog.length && <p>没有匹配的对象</p>}</div></div>}
    <OntologyGraph key={layoutKey} draft={draft} selected={selected} onSelect={select} showProperties={showProperties} />
    <dialog ref={editor} className="ontology-edit-dialog" aria-label="编辑本体对象" onCancel={event => { event.preventDefault(); close() }}>
      <div className="dialog-heading"><h2>编辑{selected.kind === 'class' ? '类' : selected.kind === 'relation' ? '关系' : '属性'}</h2><button className="icon-button" aria-label="关闭本体编辑" onClick={close}><Icon name="close" size={18} /></button></div>
      {!!selected.id && <OntologyInspector key={`${selected.kind}:${selected.id}`} draft={draft} selection={selected} materials={state.materials} onSave={save} onDirty={onDirty} />}
    </dialog>
  </section>
}
