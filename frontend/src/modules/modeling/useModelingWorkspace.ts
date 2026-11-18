import { useCallback, useEffect, useRef, useState } from 'react'
import { initialWorkspace, workspaceReducer, type WorkspaceAction, type WorkspaceState, type Material } from './state'
import { liveState, request, upload, type LiveRun, type LiveSnapshot } from './live'

export default function useModelingWorkspace() {
  const [state, setState] = useState(initialWorkspace)
  const [busy, setBusy] = useState('')
  const current = useRef(state); current.current = state
  const pending = useRef(false)
  const generateKey = useRef<{fingerprint:string;key:string} | null>(null)
  const act = useCallback(async (label:string,work:() => Promise<void>) => {
    if (pending.current) return
    pending.current=true; setBusy(label)
    try { await work() }
    catch (error) { setState(previous => ({...previous,error:error instanceof Error ? error.message : '服务请求未完成，请重新读取原记录确认状态。',notice:''})) }
    finally { pending.current=false; setBusy('') }
  },[])
  const restore = useCallback(async () => {
    const [active,runs] = await Promise.all([request<LiveSnapshot|null>('modeling/active'),request<{items:{id:string;status:string}[]}>('modeling/runs')])
    const latest = runs.items.find(item => item.status === 'succeeded')
    const run = latest ? await request<LiveRun>(`modeling/runs/${latest.id}`) : null
    if (run) setState(previous => liveState(run,{...previous,active:active ? {...active,snapshotId:active.id} : null}))
    else {
      const library=await request<{items:{id:string;revision:number;name:string;category:string}[]}>('materials')
      const materials:Material[]=[]
      for (const entry of library.items.slice(0,30)) {
        if (!/\.(sql|txt|md)$/i.test(entry.name)) continue
        const saved=await request<{body:string;size:number}>(`materials/${entry.id}/revisions/${entry.revision}/content`)
        materials.push({...entry,...saved,origin:'upload',remoteRevision:entry.revision,
          kind:entry.category === 'ddl' ? 'DDL' : entry.category === 'sql' ? '热点 SQL' : '业务说明'})
      }
      setState(previous => ({...previous,materials,selected:materials.map(item=>item.id),active:active ? {...active,snapshotId:active.id} : null,error:''}))
    }
  },[])
  useEffect(() => {
    // Unconfigured backend leaves the empty input state; it never loads synthetic results.
    void act('正在恢复服务端记录…',restore)
  },[act,restore])
  const dispatch = useCallback((action:WorkspaceAction) => {
    if (pending.current) return
    const previous = current.current
    if (action.type === 'add-materials') {
      void act('正在保存材料…',async () => {
        const saved:Material[]=[]
        for (const material of action.materials) saved.push(await upload(material))
        setState(current => ({...workspaceReducer(current,{...action,materials:saved}),live:undefined,notice:'材料已保存到后端；可以开始真实 DDL/SQL 建模。'}))
      }); return
    }
    if (previous.live && ['edit-class','edit-property','edit-relation','exclude','validate','adopt'].includes(action.type)) {
      void act('正在保存或校验服务端模型…',async () => {
        const base=`modeling/runs/${previous.live!.runId}`
        const revision=previous.draft!.revision
        if (action.type === 'adopt') {
          const snapshot=await request<LiveSnapshot>(`${base}/adopt`,{revision})
          setState(current => ({...current,active:{...snapshot,snapshotId:snapshot.id},notice:'模型快照已采用；字段溯源现在使用导出的 OWL / R2RML。',error:''}))
        } else {
          const result=await request<LiveRun>(`${base}/${action.type === 'validate' ? 'validate' : 'draft'}`,{revision,...action})
          setState(current => liveState(result,current))
        }
      }); return
    }
    setState(current => workspaceReducer(current,action))
  },[act])
  const generate = useCallback((semantic:boolean) => act('正在解析真实材料并生成本体…',async () => {
    const previous=current.current
    const selected=previous.materials.filter(item => previous.selected.includes(item.id))
    if (!selected.length) throw new Error('请先选择材料。')
    const saved=[]
    for (const material of selected) saved.push(await upload(material))
    const refs=saved.map(item => ({id:item.id,revision:item.remoteRevision!}))
    const fingerprint=JSON.stringify({refs,semantic})
    if (generateKey.current?.fingerprint !== fingerprint) generateKey.current={fingerprint,key:crypto.randomUUID()}
    const run=await request<LiveRun>('modeling/runs',{materials:refs,request_key:generateKey.current!.key,semantic})
    setState(current => liveState(run,current))
  }),[act])
  return {state,dispatch,busy,generate,reload:() => act('正在重新读取…',restore)}
}
