import type { Material, PreviewState, Snapshot } from './preview'

export type LiveRun = {
  id: string; status: string; revision: number; error: string | null
  result: { draft: NonNullable<PreviewState['draft']>; materials: { id: string; name: string; revision: number; body: string; category: string; size: number }[]
    stats: Record<string, number>; diagnostics: { code: string; message: string; materialId?: string }[]; method: string; semantic?: {accepted: number} } | null
  validation: { valid: boolean; revision: number; problems: {code: string; message: string}[]; reports: Record<string, {diagnostics: {severity: string; message: string}[]}>
    verification: {static: string; materialization: string; business_semantics: string}; losses: string[] } | null
}

export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, {credentials: 'same-origin', method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {'Content-Type':'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)})
  const value = await response.json().catch(() => null)
  if (!response.ok) throw new Error(value?.detail?.message || (typeof value?.detail === 'string' ? value.detail : `服务请求失败（${response.status}），请确认后端配置。`))
  return value as T
}

export function liveState(run: LiveRun, previous: PreviewState): PreviewState {
  if (run.status !== 'succeeded' || !run.result) throw new Error(run.error || `任务状态：${run.status}；请读取原任务，不要重复请求模型。`)
  const materials: Material[] = run.result.materials.map(item => ({...item, origin:'upload', remoteRevision:item.revision,
    kind: item.category === 'ddl' ? 'DDL' : item.category === 'sql' ? '热点 SQL' : '业务说明'}))
  return {...previous, materials, selected:materials.map(item => item.id), draft:run.result.draft, validation:null,
    live:{runId:run.id, stats:run.result.stats, diagnostics:run.result.diagnostics, method:run.result.method, check:run.validation},
    error:'', notice:run.validation ? `服务端校验${run.validation.valid ? '通过' : '存在问题'}，结果绑定草稿 r${run.revision}。` : '真实材料已完成结构与 SQL 分析，草稿已保存到后端。'}
}

export async function upload(material: Material): Promise<Material> {
  if (material.remoteRevision) return material
  if (material.kind === 'PDF') throw new Error('PDF 尚未接入正文提取；请先提供 UTF-8 文本、DDL 或 SQL。')
  const response = await fetch('/api/v1/materials', {method:'POST', credentials:'same-origin', headers:{
    'Content-Type':'text/plain;charset=utf-8', 'X-Material-Name':encodeURIComponent(material.name),
    'X-Material-Category':material.kind === 'DDL' ? 'ddl' : material.kind.includes('SQL') ? 'sql' : 'document'},body:material.body})
  const value = await response.json()
  if (!response.ok) throw new Error(value.detail?.message || '材料上传失败')
  return {...material,id:value.id,remoteRevision:value.revision}
}

export type LiveSnapshot = Snapshot & { id: string; run_id: string }
