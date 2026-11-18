import { useEffect, useState } from 'react'
import Icon from '../../shared/Icon'
import Dialog from '../../shared/Dialog'
import { upload } from '../modeling/live'
import type { Material } from '../modeling/state'
import { loadMaterials } from './materials'
import { documentSummary, readMaterial } from './document'

export default function MaterialsPage() {
  const [materials,setMaterials]=useState<Material[]>([])
  const [creating,setCreating]=useState(false)
  const [mode,setMode]=useState<'upload'|'text'>('upload')
  const [files,setFiles]=useState<File[]>([])
  const [name,setName]=useState('')
  const [body,setBody]=useState('')
  const [query,setQuery]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [preview,setPreview]=useState<Material|null>(null)
  const load=async()=>setMaterials(await loadMaterials())
  useEffect(()=>{setBusy(true);void load().catch(e=>setError(e.message)).finally(()=>setBusy(false))},[])
  const save=async()=>{
    setBusy(true);setError('');setNotice('')
    let saved=0
    try {
      const input=mode==='upload' ? files : [new File([body],/\.(md|txt|sql)$/i.test(name) ? name : name+'.md')]
      if (!input.length) throw new Error('请选择需要上传的文档。')
      for (const file of input) {await upload(await readMaterial(file));saved++}
      await load();setCreating(false);setFiles([]);setName('');setBody('');setNotice(`已保存 ${saved} 份文档。`)
    } catch(e) {setError((e instanceof Error ? e.message : '保存失败')+(saved ? ` 已保存 ${saved} 份，请勿重复上传。` : ''));if(saved) await load().catch(()=>{})}
    finally {setBusy(false)}
  }
  const filtered=materials.filter(item=>`${item.name} ${item.kind} ${documentSummary(item.body)}`.toLowerCase().includes(query.toLowerCase()))
  return <section className="workbench-page document-library-page"><div className="page-heading"><div><h1>文档材料</h1><p>统一管理上传文档与数据库采集的 DDL，建模时直接选用。</p></div><button className="button primary" disabled={busy} onClick={()=>{setCreating(true);setError('');setFiles([])}}><Icon name="plus" size={16}/>新建文档</button></div>
    {!creating&&error&&<p className="message error" role="alert">{error}</p>}{notice&&<p className="message info" role="status">{notice}</p>}
    <div className="catalog-toolbar"><div className="search-box"><Icon name="search" size={15}/><input aria-label="搜索文档" placeholder="搜索文档名称或说明" value={query} onChange={e=>setQuery(e.target.value)}/></div><span className="subtle">{filtered.length} 份文档</span><button className="icon-button" aria-label="刷新文档列表" disabled={busy} onClick={()=>{setBusy(true);void load().catch(e=>setError(e.message)).finally(()=>setBusy(false))}}><Icon name="refresh" size={16}/></button></div>
    {busy&&!creating&&<p className="operation-status" role="status">正在读取文档…</p>}
    <div className="document-table table-scroll"><table><thead><tr><th>文档名称</th><th>类型</th><th>文档介绍</th><th>版本 / 大小</th><th>操作</th></tr></thead><tbody>{filtered.map(item=><tr key={`${item.id}:${item.remoteRevision}`}><td><button className="document-name" onClick={()=>setPreview(item)}><Icon name={item.kind==='DDL'||item.kind.includes('SQL')?'code':'file'} size={17}/><span>{item.name}</span></button></td><td><span className="document-type">{item.kind}</span></td><td className="document-description">{documentSummary(item.body)}</td><td><span className="document-meta">r{item.remoteRevision} · {Math.max(1,Math.ceil(item.size/1024))} KB</span></td><td><button className="text-button" onClick={()=>setPreview(item)}>查看</button></td></tr>)}</tbody></table>{!filtered.length&&!busy&&<div className="document-list-empty"><Icon name="file" size={26}/><p>{materials.length?'没有匹配的文档':'暂无文档，点击右上角“新建文档”添加。'}</p></div>}</div>
    {creating&&<Dialog title="新建文档" onClose={()=>{if(!busy)setCreating(false)}}><form className="workbench-form document-create-form" onSubmit={e=>{e.preventDefault();void save()}}><div className="segmented" aria-label="文档创建方式"><button type="button" aria-pressed={mode==='upload'} disabled={busy} onClick={()=>setMode('upload')}><Icon name="upload" size={15}/>上传文件</button><button type="button" aria-pressed={mode==='text'} disabled={busy} onClick={()=>setMode('text')}><Icon name="edit" size={15}/>粘贴正文</button></div>{mode==='upload'?<label>选择文件<input type="file" multiple accept=".sql,.txt,.md" disabled={busy} onChange={e=>setFiles([...e.target.files??[]])}/><small>SQL / TXT / Markdown，UTF-8 编码，每份最多 2 MB。</small></label>:<><label>文档名称<input required maxLength={150} value={name} disabled={busy} onChange={e=>setName(e.target.value)} placeholder="输入文档名称"/></label><label>文档正文<textarea required rows={9} maxLength={200000} value={body} disabled={busy} onChange={e=>setBody(e.target.value)} placeholder="粘贴 DDL、SQL 或业务文档正文"/></label></>}{error&&<p className="message error" role="alert">{error}</p>}<div className="dialog-footer"><button type="button" className="button secondary" disabled={busy} onClick={()=>setCreating(false)}>取消</button><button className="button primary" disabled={busy||(mode==='upload'?!files.length:!name.trim()||!body.trim())}>{busy?'正在保存…':'保存文档'}</button></div></form></Dialog>}
    {preview&&<Dialog title={preview.name} wide onClose={()=>setPreview(null)}><p className="small-note">{preview.kind} · r{preview.remoteRevision} · {Math.max(1,Math.ceil(preview.size/1024))} KB</p><pre className="document-preview">{preview.body||'此格式暂不支持正文预览，请转换为 UTF-8 SQL、TXT 或 Markdown 后重新接入。'}</pre></Dialog>}
  </section>
}
