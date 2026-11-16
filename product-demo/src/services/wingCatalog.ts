import type { Workspace } from '../domain/types'
import { reference } from './seed'

export const MODEL_ID = 'sgtrace'

// 仅为独立原型的 OntoWing 组件提供本地目录；不拦截其他 API，也不发起真实数据库访问。
export function installWingCatalog(read: () => Workspace) {
  const original = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.href)
    if (url.origin === window.location.origin && (!init?.method || init.method === 'GET')) {
      if (url.pathname === `/api/v1/models/${MODEL_ID}/fact-planes`) {
        const items = read().sources.flatMap(source => source.tables.map(table => ({
          reference: reference(source.database, table.name, source.id),
          dictionary: { table_name: table.name, columns: table.columns.map(({ label: _label, ...column }) => column) },
        })))
        return Response.json({ profile: 'current-fact-plane-definitions/2', workspace_id: MODEL_ID,
          provider: 'local_mock', simulated: true, items, vdb_names: { 'local-demo': '已接入数据源' } })
      }
      if (url.pathname === '/api/v1/modeling-references') return Response.json({ items: [], total: 0 })
    }
    return original(input, init)
  }
  return () => { window.fetch = original }
}
