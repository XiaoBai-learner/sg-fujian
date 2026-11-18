import { useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import type { WorkspaceState, WorkspaceAction } from './state'

export default function MaterialPicker({state,dispatch,onSources}:{state:WorkspaceState;dispatch:Dispatch<WorkspaceAction>;onSources:()=>void}) {
  const [expanded,setExpanded]=useState<string|null>(null)
  const [query,setQuery]=useState('')
  const library=state.materials.filter(item=>!item.id.startsWith('context-')&&/\.(sql|txt|md)$/i.test(item.name))
  const filtered=library.filter(item=>`${item.name} ${item.kind}`.toLowerCase().includes(query.toLowerCase()))
  return <section className="model-material-picker" aria-label="选择已接入材料"><div className="catalog-toolbar"><div className="search-box"><Icon name="search" size={15}/><input aria-label="筛选已接入材料" placeholder="搜索已有材料" value={query} onChange={e=>setQuery(e.target.value)}/></div><button className="text-button" onClick={onSources}>前往数据源接入<Icon name="arrow" size={14}/></button></div>
    <div className="table-scroll"><table><thead><tr><th>选用</th><th>材料名称</th><th>类型</th><th>版本</th><th>正文</th></tr></thead><tbody>{filtered.map(item=><tr key={item.id}><td><input aria-label={`选择 ${item.name}`} type="checkbox" checked={state.selected.includes(item.id)} onChange={()=>dispatch({type:'toggle-material',id:item.id})}/></td><td>{item.name}</td><td>{item.kind}</td><td>r{item.remoteRevision}</td><td><button className="text-button" onClick={()=>setExpanded(expanded===item.id?null:item.id)}>{expanded===item.id?'收起':'查看'}</button></td></tr>)}</tbody></table></div>
    {!filtered.length&&<p className="small-note">暂无可选材料，请先在数据源接入中添加数据库结构或文档。</p>}{expanded&&<pre className="document-preview">{library.find(item=>item.id===expanded)?.body}</pre>}
  </section>
}
