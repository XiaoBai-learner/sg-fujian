import type { Material } from '../modeling/state'
import { request } from '../modeling/live'


export async function loadMaterials(): Promise<Material[]> {
  const library=await request<{items:{id:string;revision:number;name:string;category:string;parse_status:string;size_bytes:number}[]}>('materials')
  return Promise.all(library.items.map(async entry => {
    const supported=/\.(sql|txt|md)$/i.test(entry.name)
    const content=supported ? await request<{body:string;size:number}>(`materials/${entry.id}/revisions/${entry.revision}/content`) : {body:'',size:entry.size_bytes}
    return {...entry,...content,origin:'upload' as const,remoteRevision:entry.revision,
      kind:(entry.category==='ddl' ? 'DDL' : entry.category==='sql' ? '热点 SQL' : '业务说明') as Material['kind'], supported}
  }))
}