export function groupModels<T extends { group: string }>(models: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>()
  for (const model of models) groups.set(model.group, [...groups.get(model.group) ?? [], model])
  return [...groups]
}
export const modelPath = (id: string) => `/modeling/${encodeURIComponent(id)}`
export function modelIdFromPath(path: string) {
  const match = /^\/modeling\/([^/]+)$/.exec(path)
  if (!match) return null
  try { return decodeURIComponent(match[1]) } catch { return null }
}
export type ModelEntry = { id: string; name: string; group: string; run_id: string | null; adopted_id: string | null; class_count: number; relation_count: number; created_at: string }
