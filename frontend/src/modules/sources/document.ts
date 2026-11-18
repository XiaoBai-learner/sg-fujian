import type { Material } from '../modeling/state'

export async function readMaterial(file: File): Promise<Material> {
  if (!/\.(sql|txt|md)$/i.test(file.name)) throw new Error(`${file.name}：请使用 SQL、TXT 或 Markdown。`)
  if (file.size > 2_000_000) throw new Error(`${file.name}：每份文档最多 2 MB。`)
  let body: string
  try { body = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer()) }
  catch { throw new Error(`${file.name}：请使用 UTF-8 编码。`) }
  if (!body.trim() || body.includes('\0')) throw new Error(`${file.name}：没有可用的文本正文。`)
  return {id:crypto.randomUUID(),name:file.name,size:file.size,body,origin:'upload',kind:/\.sql$/i.test(file.name) ? /\bCREATE\s+TABLE\b/i.test(body) ? 'DDL' : '热点 SQL' : '业务说明'}
}

export function documentSummary(body: string) {
  return body.split(/\r?\n/).map(line=>line.trim().replace(/^#+\s*/, '')).find(Boolean)?.slice(0,140) ?? '暂无正文摘要'
}
