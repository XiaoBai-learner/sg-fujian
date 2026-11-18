import { useCallback, useEffect, useRef, useState } from 'react'
import { initialWorkspace, workspaceReducer, type WorkspaceAction, type WorkspaceState } from './state'
import { liveState, request, type LiveRun, type LiveSnapshot } from './live'

import { loadMaterials } from '../sources/materials'

export default function useModelingWorkspace(modelId: string | null) {
  const [state, setState] = useState(initialWorkspace)
  const [busy, setBusy] = useState('')
  const [businessContext, setBusinessContext] = useState('')
  const context = useRef(''); context.current = businessContext
  const persistedContext = useRef('')
  const current = useRef(state); current.current = state
  const selectedModel = useRef(modelId); selectedModel.current = modelId
  const pending = useRef(false)
  const generateKey = useRef<{ fingerprint: string; key: string } | null>(null)
  const act = useCallback(async (label: string, work: () => Promise<void>) => {
    if (pending.current) return false
    pending.current = true; setBusy(label)
    try { await work(); return true }
    catch (error) { setState(previous => ({ ...previous, error: error instanceof Error ? error.message : '请求未完成，请重新读取服务端记录。', notice: '' })); return false }
    finally { pending.current = false; setBusy('') }
  }, [])
  const restore = useCallback(async () => {
    const id = selectedModel.current
    const [library, detail] = await Promise.all([
      loadMaterials(),
      id ? request<{ run: LiveRun | null; active: LiveSnapshot | null; business_context: string }>(`modeling/models/${id}`) : Promise.resolve({ run: null, active: null, business_context: '' }),
    ])
    const materials = library
    if (id !== selectedModel.current) return
    persistedContext.current=detail.business_context
    setBusinessContext(detail.business_context)
    const base: WorkspaceState = { ...initialWorkspace(), materials, active: detail.active ? { ...detail.active, snapshotId: detail.active.id } : null }
    if (detail.run) {
      const next = liveState(detail.run, base)
      setState({ ...next, materials:[...materials,...next.materials.filter(item=>item.source_kind==='model_context')], notice: '' })
    } else setState(base)
  }, [])
  useEffect(() => {
    setState(initialWorkspace())
    void act('正在读取工作区…', restore)
  }, [modelId, act, restore])
  const dispatch = useCallback((action: WorkspaceAction) => {
    if (pending.current) return
    const previous = current.current
    if (previous.live && ['edit-class', 'edit-property', 'edit-relation', 'exclude', 'validate', 'adopt'].includes(action.type)) {
      void act('正在保存到服务端…', async () => {
        const base = `modeling/runs/${previous.live!.runId}`
        const revision = previous.draft!.revision
        if (action.type === 'adopt') {
          const snapshot = await request<LiveSnapshot>(`${base}/adopt`, { revision })
          setState(current => ({ ...current, active: { ...snapshot, snapshotId: snapshot.id }, notice: '当前模型版本已采用，可进行字段溯源。', error: '' }))
        } else {
          const result = await request<LiveRun>(`${base}/${action.type === 'validate' ? 'validate' : 'draft'}`, { revision, ...action })
          setState(current => ({ ...liveState(result, current), materials: current.materials, notice: action.type === 'validate' ? (result.validation?.valid ? '静态校验通过。' : '校验存在问题，请查看报告。') : '草稿修改已保存；重新校验后可采用。' }))
        }
      }); return
    }
    setState(current => workspaceReducer(current, action))
  }, [act])
  const generate = useCallback((semantic: boolean) => act('正在分析材料并生成本体…', async () => {
    const previous = current.current
    const selected = previous.materials.filter(item => item.source_kind!=='model_context' && previous.selected.includes(item.id))
    if (!selected.length || !selectedModel.current) throw new Error('请在模型中选择建模材料。')
    const text=context.current.trim()
    if (text !== persistedContext.current) { await request(`modeling/models/${selectedModel.current}/context`,{text}); persistedContext.current=text;setBusinessContext(text) }
    const refs = selected.map(item => ({ id: item.id, revision: item.remoteRevision! }))
    const fingerprint = JSON.stringify({ refs, semantic, context:text, model: selectedModel.current })
    if (generateKey.current?.fingerprint !== fingerprint) generateKey.current = { fingerprint, key: crypto.randomUUID() }
    const run = await request<LiveRun>('modeling/runs', { materials: refs, request_key: generateKey.current!.key, semantic, model_id: selectedModel.current })
    setState(current => { const next=liveState(run,current); return {...next, materials:[...current.materials.filter(item=>item.source_kind!=='model_context'),...next.materials.filter(item=>item.source_kind==='model_context')]} })
  }), [act])
  const saveContext = (text:string) => act('正在保存业务流程…', async () => {
    if(!selectedModel.current) throw new Error('请先选择本体模型。')
    const result=await request<{business_context:string}>(`modeling/models/${selectedModel.current}/context`,{text})
    persistedContext.current=result.business_context
    setBusinessContext(result.business_context)
  })
  return { state, dispatch, busy, generate, businessContext, saveContext, reload: () => act('正在重新读取…', restore) }
}
