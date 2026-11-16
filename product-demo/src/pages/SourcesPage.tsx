import { useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import type { Page, Source, Workspace } from '../domain/types'
import Icon from '../components/Icon'
import Dialog from '../components/Dialog'
import { readModelingFiles } from '../services/modeling'

export default function SourcesPage({ state, onChange, onNavigate }: {
  state: Workspace; onChange: Dispatch<SetStateAction<Workspace>>; onNavigate: (page: Page) => void
}) {
  const [modal, setModal] = useState(false)
  const [browse, setBrowse] = useState<Source>()
  const [tableIndex, setTableIndex] = useState(0)
  const [kind, setKind] = useState('DDL')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [reading, setReading] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState({ name: '', host: '', database: '', type: 'MySQL', port: '3306', username: '', password: '' })
  const save = (event: FormEvent) => {
    event.preventDefault()
    if (!form.name.trim() || !form.host.trim() || !form.database.trim()) return
    onChange({ ...state, sources: [...state.sources, { id: String(Date.now()), name: form.name, host: `${form.host}:${form.port}`, database: form.database, type: form.type, tables: [] }] })
    setModal(false)
    setForm({ name: '', host: '', database: '', type: 'MySQL', port: '3306', username: '', password: '' })
    setMessage('连接配置已保存在本地。原型未连接数据库，也未保存账号或口令。')
  }
  const addFiles = async (files: FileList | null) => {
    if (!files?.length) return
    setReading(true); setError('')
    try {
      const materials = await readModelingFiles([...files])
      onChange(current => ({ ...current, materials: [...current.materials, ...materials.map(material => ({ ...material, kind: material.kind === 'DDL' ? 'DDL' : kind }))] }))
      setMessage('材料已加入建模材料库。文本和 DDL 可用于本地草稿预览，PDF 等待后端解析。')
    } catch (error) { setError(error instanceof Error ? error.message : '材料读取失败。') }
    finally { setReading(false) }
  }
  const table = browse?.tables[tableIndex]
  return <>
    <div className="module-heading"><div><h1>数据源接入</h1><p>连接数据库，或添加已有的数据材料。</p></div><button className="action primary" onClick={() => setModal(true)}><Icon name="plus" />添加数据源</button></div>
    <section className="plain-section">
      <div className="section-title"><h2>数据源 <span>{state.sources.length}</span></h2><small>采集表结构，不读取业务数据</small></div>
      <div className="source-list">{state.sources.map(source => <article className="source-card" key={source.id}>
        <span className="source-icon"><Icon name="source" /></span>
        <div className="source-info"><h3>{source.name}<span className="subtle-tag">{source.type}</span></h3><p>{source.database} <span>·</span> {source.host}</p></div>
        <span className={`status-label ${source.tables.length ? 'good' : ''}`}><i />{source.tables.length ? `${source.tables.length} 张表` : '待采集'}</span>
        <button className="text-action" disabled={!source.tables.length} onClick={() => { setBrowse(source); setTableIndex(0) }}>浏览结构 <span>↗</span></button>
      </article>)}</div>
    </section>
    <section className="plain-section materials-section">
      <div className="section-title"><div><h2>补充材料 <span>{state.materials.length}</span></h2><p>DDL 与业务文档可直接选用于本体建模。</p></div><div className="compact-actions"><select aria-label="材料类型" value={kind} onChange={e => setKind(e.target.value)}>{['DDL', '血缘导出', '任务 SQL', '业务说明'].map(k => <option key={k}>{k}</option>)}</select><button className="action" disabled={reading} onClick={() => fileInput.current?.click()}><Icon name="plus" />{reading ? '读取中…' : '添加材料'}</button><input type="file" accept=".sql,.txt,.md,.pdf,.csv,.json" multiple ref={fileInput} hidden onChange={e => { void addFiles(e.target.files); e.target.value = '' }} /></div></div>
      <div className="material-list">{state.materials.map(material => <div className="material-row" key={material.id}><Icon name="file" /><span>{material.name}</span><span className="subtle-tag">{material.kind}</span><small>{(material.size / 1024).toFixed(1)} KB</small></div>)}</div>
      {message && <p className="inline-note" role="status">{message}</p>}
      {error && <p className="error-note" role="alert">{error}</p>}
    </section>
    <div className="next-step"><span>数据结构已就绪？</span><button className="text-action" onClick={() => onNavigate('modeling')}>前往本体建模<Icon name="arrow" /></button></div>
    {modal && <Dialog titleId="source-title" onClose={() => setModal(false)}><form onSubmit={save}><div className="dialog-heading"><div><h2 id="source-title">添加数据源</h2><p>配置只读数据库连接。</p></div><button type="button" className="icon-button" aria-label="关闭" onClick={() => setModal(false)}>×</button></div><div className="input-grid">
      <label className="full">连接名称<input required autoFocus value={form.name} placeholder="例如：营销业务库" onChange={e => setForm({ ...form, name: e.target.value })} /></label>
      <label>数据库类型<select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}><option>MySQL</option><option>Oracle</option><option>PostgreSQL</option></select></label><label>数据库 / Schema<input required value={form.database} onChange={e => setForm({ ...form, database: e.target.value })} /></label>
      <label>主机<input required value={form.host} onChange={e => setForm({ ...form, host: e.target.value })} placeholder="数据库地址" /></label><label>端口<input required type="number" min="1" max="65535" value={form.port} onChange={e => setForm({ ...form, port: e.target.value })} /></label>
      <label>只读账号<input autoComplete="off" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></label><label>密码<input type="password" autoComplete="new-password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>
    </div><p className="inline-note">原型仅演示配置操作，不建立真实连接，不保存凭据。</p><div className="dialog-actions"><button type="button" className="action" onClick={() => setModal(false)}>取消</button><button className="action primary" type="submit">保存配置</button></div></form></Dialog>}
    {browse && <Dialog wide titleId="browse-title" onClose={() => setBrowse(undefined)}><div className="dialog-heading"><div><h2 id="browse-title">{browse.name}</h2><p>{browse.database} / 表结构</p></div><button className="icon-button" aria-label="关闭" onClick={() => setBrowse(undefined)}>×</button></div><div className="schema-browser"><nav aria-label="数据表">{browse.tables.map((table, index) => <button aria-current={index === tableIndex ? 'true' : undefined} key={table.name} onClick={() => setTableIndex(index)}><strong>{table.label}</strong><code>{table.name}</code></button>)}</nav><div className="table-scroll"><table className="clean-table"><thead><tr><th>字段</th><th>中文名</th><th>类型</th><th>主键</th></tr></thead><tbody>{table?.columns.map(column => <tr key={column.name}><td><code>{column.name}</code></td><td>{column.label}</td><td>{column.data_type}</td><td>{column.primary_key ? '是' : '—'}</td></tr>)}</tbody></table></div></div></Dialog>}
  </>
}
