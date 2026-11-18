import { useEffect, useState } from 'react'
import Icon from '../../shared/Icon'
import Dialog from '../../shared/Dialog'
import { api } from '../../shared/api/session'
import { groupModels, modelPath, type ModelEntry } from './catalog'

export default function ModelCatalog({ navigate }: { navigate: (path: string) => void }) {
  const [models, setModels] = useState<ModelEntry[]>([])
  const [query, setQuery] = useState('')
  const [group, setGroup] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<ModelEntry | null>(null)
  const [name, setName] = useState('')
  const [newGroup, setNewGroup] = useState('未分组')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = () => api<{ items: ModelEntry[] }>('modeling/models').then(data => setModels(data.items))
  useEffect(() => { void load().catch(error => setError(error.message)) }, [])
  const groups = groupModels(models)
  const filtered = models.filter(model => (!group || model.group === group) && `${model.name} ${model.group}`.toLowerCase().includes(query.toLowerCase()))
  const openCreate = () => { setEditing(null); setName(''); setNewGroup(!group ? '未分组' : group); setError(''); setCreating(true) }
  return <section className="workbench-page model-library-page">
    <div className="page-heading"><div><h1>本体模型</h1><p>按业务分组管理模型，独立建模、编辑和采用。</p></div><button className="button primary" onClick={openCreate}><Icon name="plus" size={17} />新建模型</button></div>
    <div className="catalog-toolbar"><div className="search-box"><Icon name="search" size={16} /><input aria-label="搜索本体模型" placeholder="搜索模型" value={query} onChange={event => setQuery(event.target.value)} /></div><label className="inline-filter">分组<select aria-label="筛选模型分组" value={group} onChange={event => setGroup(event.target.value)}><option value="">不限分组</option>{groups.map(([name]) => <option key={name} value={name}>{name}</option>)}</select></label><span className="subtle">{filtered.length} 个模型</span></div>
    <div className="model-catalog-content">
        {error && !creating && <p className="message error" role="alert">{error}</p>}
        {!filtered.length ? <div className="empty-state"><Icon name="model" size={36} /><h2>{models.length ? '没有匹配的模型' : '创建第一个本体模型'}</h2><p>命名模型，选择材料，再进入本体画布。</p><button className="button secondary" onClick={openCreate}>新建模型</button></div> : <div className="model-card-grid">{filtered.map(model => <article className="model-card" key={model.id}><button className="model-card-open" onClick={() => navigate(modelPath(model.id))}><span className="model-card-icon"><Icon name="model" size={23} /></span><h3>{model.name}</h3><p>{model.group}</p><div><span>{model.class_count} 个类 · {model.relation_count} 条关系</span><span className={`status-label ${model.adopted_id ? 'available' : ''}`}>{model.adopted_id ? '已采用' : model.run_id ? '草稿' : '未建模'}</span></div></button><button className="model-card-edit icon-button" aria-label={`编辑模型 ${model.name}`} onClick={() => { setEditing(model); setName(model.name); setNewGroup(model.group); setError(''); setCreating(true) }}><Icon name="edit" size={15} /></button></article>)}</div>}
    </div>
    {creating && <Dialog title={editing ? '编辑模型信息' : '新建本体模型'} onClose={() => { if (!busy) setCreating(false) }}><form className="workbench-form" onSubmit={event => { event.preventDefault(); setBusy(true); setError(''); void api<ModelEntry>(editing ? `modeling/models/${editing.id}` : 'modeling/models', { name, group: newGroup }, editing ? 'PATCH' : 'POST').then(async model => { await load(); setCreating(false); if (!editing) navigate(modelPath(model.id)) }).catch(error => setError(error.message)).finally(() => setBusy(false)) }}>
      <label>模型名称<input autoFocus required maxLength={160} value={name} onChange={event => setName(event.target.value)} placeholder="为本体模型命名" /></label><label>所属分组<input required maxLength={160} value={newGroup} list="model-group-options" onChange={event => setNewGroup(event.target.value)} /></label><datalist id="model-group-options">{groups.map(([name]) => <option key={name} value={name} />)}</datalist><p className="small-note">分组仅用于整理。各模型的草稿、材料引用及采用版本相互独立。</p>{error && <p className="message error" role="alert">{error}</p>}<div className="dialog-footer"><button className="button secondary" type="button" disabled={busy} onClick={() => setCreating(false)}>取消</button><button className="button primary" disabled={busy || !name.trim() || !newGroup.trim()}>{busy ? '正在保存…' : editing ? '保存' : '创建模型'}</button></div>
    </form></Dialog>}
  </section>
}
