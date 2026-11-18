import { useEffect, useState } from 'react'
import Icon from '../../shared/Icon'
import Dialog from '../../shared/Dialog'
import { api } from '../../shared/api/session'

type Source = { id: string; name: string; kind: string; database: string | null; status: string; host: string | null; port: number; username: string | null; has_password: boolean; databases: string[] }
type Config = { name: string; host: string; port: number; username: string; password: string; databases: string[] }
const empty: Config = { name: '', host: '', port: 3306, username: '', password: '', databases: [] }
export default function SourcesPage({ onMaterials }: { onMaterials: () => void }) {
  const [sources, setSources] = useState<Source[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [available, setAvailable] = useState<string[]>([])
  const [databases, setDatabases] = useState<string[]>([])
  const [editing, setEditing] = useState<Source | 'new' | null>(null)
  const [config, setConfig] = useState<Config>(empty)
  const [probe, setProbe] = useState<string[]>([])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const current = sources.find(item => item.id === selected)
  const load = async () => { const data = await api<{ items: Source[] }>('sources'); setSources(data.items) }
  const act = async (label: string, work: () => Promise<void>) => {
    setBusy(label); setError(''); setNotice('')
    try { await work() } catch (e) { setError(e instanceof Error ? e.message : '操作失败') } finally { setBusy('') }
  }
  useEffect(() => { void act('正在读取连接…', load) }, [])
  const open = (source: Source | 'new') => {
    setEditing(source); setError(''); setNotice(''); setProbe([])
    setConfig(source === 'new' ? empty : { name: source.name, host: source.host ?? '', port: source.port, username: source.username ?? '', password: '', databases: source.databases })
  }
  const choose = (source: Source) => { setSelected(source.id); setDatabases(source.databases); setAvailable(source.databases); setQuery('') }
  const payload = () => ({ ...config, name: config.name.trim() || '未命名连接', kind: 'mysql', source_id: editing !== 'new' ? editing?.id : undefined, password: editing !== 'new' && !config.password ? null : config.password })
  const shown = available.filter(name => name.toLowerCase().includes(query.toLowerCase()))
  return <section className="workbench-page">
    <div className="page-heading"><div><h1>数据源</h1><p>管理数据库连接，选择需要建模的数据库。</p></div><button className="button primary" onClick={() => open('new')}><Icon name="plus" size={17} />新建连接</button></div>
    {!editing && error && <p className="message error" role="alert">{error}</p>}
    {notice && !editing && <p className="message info" role="status">{notice}</p>}
    {busy && <p className="operation-status" role="status">{busy}</p>}
    <div className="connection-workbench">
      <section className="connection-list"><div className="list-caption">连接 <span>{sources.length}</span><button className="icon-button" aria-label="刷新连接列表" disabled={!!busy} onClick={() => void act('正在刷新…', load)}><Icon name="refresh" size={15} /></button></div>
        {!sources.length && <div className="small-empty"><Icon name="source" size={28} /><strong>还没有数据库连接</strong><p>创建连接后选择一个或多个库。</p></div>}
        {sources.map(source => <button className={`connection-row ${selected === source.id ? 'selected' : ''}`} key={source.id} onClick={() => choose(source)}><Icon name="source" size={20} /><span><strong>{source.name}</strong><small>{source.host ? `${source.host}:${source.port}` : '服务端配置连接'}</small></span><Icon name="chevron" size={14} /></button>)}
      </section>
      <section className="connection-detail">{current ? <>
        <div className="section-heading"><div><h2>{current.name}</h2><p><code>{current.username ?? '—'}@{current.host ?? '服务端配置'}:{current.port}</code></p></div><div className="toolbar-actions"><button className="button secondary" disabled={!!busy} onClick={() => void act('正在测试连接…', async () => { await api(`sources/${current.id}/test`, {}); setNotice('连接成功。'); await load() })}>测试连接</button><button className="button secondary" onClick={() => open(current)}><Icon name="edit" size={15} />编辑连接</button></div></div>
        <div className="database-heading"><h3>数据库</h3><button className="text-button" disabled={!!busy} onClick={() => void act('正在读取数据库…', async () => { const data = await api<{ items: string[] }>(`sources/${current.id}/databases`); setAvailable(data.items) })}><Icon name="refresh" size={14} />读取数据库</button></div>
        <div className="database-filter"><Icon name="search" size={16} /><input aria-label="筛选数据库" placeholder="搜索数据库" value={query} onChange={event => setQuery(event.target.value)} /></div>
        <label className="checkbox-row database-select-all"><input type="checkbox" checked={!!shown.length && shown.every(name => databases.includes(name))} onChange={event => setDatabases(event.target.checked ? [...new Set([...databases, ...shown])] : databases.filter(name => !shown.includes(name)))} />全选<span>{databases.length} 个已选</span></label>
        <div className="database-list">{shown.map(name => <label className="checkbox-row" key={name}><input type="checkbox" checked={databases.includes(name)} onChange={event => setDatabases(event.target.checked ? [...databases, name] : databases.filter(item => item !== name))} /><Icon name="source" size={16} /><code>{name}</code></label>)}{!shown.length && <p className="small-note">点击“读取数据库”查看此连接可访问的库。</p>}</div>
        <div className="connection-footer"><button className="button secondary" disabled={!!busy} onClick={() => void act('正在保存选择…', async () => { await api(`sources/${current.id}`, { name: current.name, kind: current.kind, host: current.host, port: current.port, username: current.username, password: null, databases }, 'PATCH'); await load(); setNotice('数据库选择已保存。') })}>保存选择</button>
          <button className="button primary" disabled={!!busy || !databases.length} onClick={() => void act('正在采集 DDL 结构…', async () => { await api(`sources/${current.id}`, { name: current.name, kind: current.kind, host: current.host, port: current.port, username: current.username, password: null, databases }, 'PATCH'); await api(`sources/${current.id}/materials`, {}); await load(); setNotice('DDL 结构已保存到文档材料，可在本体模型内选用。') })}><Icon name="file" size={16} />采集结构到材料</button><button className="text-button" onClick={onMaterials}>查看材料<Icon name="arrow" size={14} /></button></div>
        <p className="small-note">仅采集结构、注释及约束，不执行取数 SQL，不修改源数据库。</p>
      </> : <div className="empty-state"><Icon name="source" size={34} /><h2>连接你的数据库</h2><p>从左侧选择连接，或创建新的 MySQL 连接。</p><button className="button secondary" onClick={() => open('new')}>新建连接</button></div>}</section>
    </div>
    {editing && <Dialog title={editing === 'new' ? '新建数据库连接' : '编辑数据库连接'} onClose={() => { if (!busy) setEditing(null) }}>
      <form className="workbench-form" onSubmit={event => { event.preventDefault(); void act('正在保存连接…', async () => { const saved = await api<Source>(editing === 'new' ? 'sources' : `sources/${editing.id}`, payload(), editing === 'new' ? 'POST' : 'PATCH'); await load(); choose(saved); setEditing(null) }) }}>
        <label>连接名称<input required maxLength={160} value={config.name} onChange={event => setConfig({ ...config, name: event.target.value })} /></label>
        <div className="form-grid"><label>主机<input required autoComplete="off" value={config.host} onChange={event => { setConfig({ ...config, host: event.target.value }); setProbe([]) }} placeholder="主机地址" /></label><label>端口<input type="number" required min={1} max={65535} value={config.port} onChange={event => setConfig({ ...config, port: Number(event.target.value) })} /></label></div>
        <label>用户名<input required autoComplete="off" value={config.username} onChange={event => setConfig({ ...config, username: event.target.value })} /></label>
        <label>密码<input type="password" autoComplete="new-password" value={config.password} placeholder={editing !== 'new' && editing.has_password ? '留空保留已保存的密码' : '数据库密码'} onChange={event => setConfig({ ...config, password: event.target.value })} /></label>
        {!!probe.length && <fieldset className="probe-databases"><legend>选择数据库</legend><label className="checkbox-row"><input type="checkbox" checked={probe.every(name => config.databases.includes(name))} onChange={event => setConfig({ ...config, databases: event.target.checked ? probe : [] })} />全选</label>{probe.map(name => <label className="checkbox-row" key={name}><input type="checkbox" checked={config.databases.includes(name)} onChange={event => setConfig({ ...config, databases: event.target.checked ? [...config.databases, name] : config.databases.filter(item => item !== name) })} /><code>{name}</code></label>)}</fieldset>}
        {error && <p role="alert" className="message error">{error}</p>}{notice && <p role="status" className="message info">{notice}</p>}
        <div className="dialog-footer"><button type="button" className="button secondary" disabled={!!busy || !config.host || !config.username} onClick={() => void act('正在测试连接…', async () => { const result = await api<{ databases: string[] }>('sources/probe', payload()); setProbe(result.databases); setNotice(`连接成功，可访问 ${result.databases.length} 个数据库。`) })}>测试连接</button><span /><button type="button" className="button secondary" disabled={!!busy} onClick={() => setEditing(null)}>取消</button><button type="submit" className="button primary" disabled={!!busy}>保存连接</button></div>
      </form>
    </Dialog>}
  </section>
}
