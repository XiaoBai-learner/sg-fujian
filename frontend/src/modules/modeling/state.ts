/** Formal workspace contracts and local edit validation; facts come from the API. */
export type Material = {
  id: string; name: string; kind: 'DDL' | '热点 SQL' | '任务 SQL' | '业务说明' | 'PDF'
  origin: 'upload'; body: string; size: number; remoteRevision?: number; source_kind?: 'model_context'
}
export type Evidence = { materialId: string; label: string; quote: string }
export type Candidate = {
  id: string; name: string; aliases: string[]; concept: string; description: string
  conceptId: string | null; datatype: 'string' | 'integer' | 'decimal' | 'boolean' | 'date' | 'datetime'; unit: string
  kind: 'direct' | 'calculated'; sources: string[]; evidence: Evidence[]
  uncertain?: boolean; excluded?: boolean; expression?: string; scope?: string; edited?: boolean
}
export type OntologyClass = {
  id: string; name: string; aliases: string[]; description: string; parentId: string | null; evidence: Evidence[]; edited?: boolean
}
export type OntologyRelation = {
  id: string; name: string; description: string; sourceId: string; targetId: string
  cardinality: 'unknown' | 'one-to-one' | 'one-to-many' | 'many-to-one' | 'many-to-many'
  symmetric: boolean; transitive: boolean; functional: boolean
  evidence: Evidence[]; uncertain?: boolean; edited?: boolean
}
export type OntologyDraft = { revision: number; items: Candidate[]; classes: OntologyClass[]; relations: OntologyRelation[] }
export type Snapshot = { snapshotId?: string; version: number; items: Candidate[]; classes: OntologyClass[]; relations: OntologyRelation[] }
export type TraceResult = {
  field: string; status: 'located' | 'not_found' | 'ambiguous'; kind?: Candidate['kind']
  sources: string[]; item?: Candidate; confidence?: number; confidence_label?: string; confidence_basis?: string; candidates?: TraceResult[]
}
export type ValidationCase = { field: string; expected: string[]; actual: string[]; passed: boolean; skipped: boolean; note: string }
export type WorkspaceState = {
  live?: { runId: string; stats: Record<string, number>; diagnostics: {code: string; message: string}[]; method: string; check: import('./live').LiveRun['validation'] };
  materials: Material[]; selected: string[]
  draft: OntologyDraft | null
  validation: { revision: number; cases: ValidationCase[] } | null
  active: Snapshot | null; error: string; notice: string
}
export type WorkspaceAction =
  | { type: 'add-materials'; materials: Material[] }
  | { type: 'toggle-material'; id: string }
  | { type: 'exclude'; id: string; excluded: boolean }
  | { type: 'edit-class'; value: OntologyClass } | { type: 'edit-property'; value: Candidate }
  | { type: 'edit-relation'; value: OntologyRelation }
  | { type: 'validate' } | { type: 'adopt' } | { type: 'clear-message' }

export function ontologyIssues(draft: OntologyDraft): string[] {
  const issues: string[] = []
  const ids = new Set(draft.classes.map(item => item.id))
  const validText = (value: string) => typeof value === 'string' && value.trim().length > 0 && value.length <= 160 && !/[\u0000-\u001f]/.test(value)
  const names = new Set<string>()
  for (const cls of draft.classes) {
    if (!validText(cls.name)) issues.push('类名称不能为空、过长或包含控制字符。')
    if (names.has(cls.name)) issues.push('类名称不能重复。')
    names.add(cls.name)
    const visited = new Set([cls.id])
    let parent = cls.parentId
    while (parent) {
      if (!ids.has(parent)) { issues.push('父类不存在。'); break }
      if (visited.has(parent)) { issues.push('父类关系不能包含循环。'); break }
      visited.add(parent)
      parent = draft.classes.find(item => item.id === parent)!.parentId
    }
  }
  const attributes = new Set<string>()
  for (const item of draft.items) {
    if (!validText(item.name)) issues.push('属性名称不能为空、过长或包含控制字符。')
    if ((item.conceptId === null && !item.uncertain) || (item.conceptId !== null && !ids.has(item.conceptId))) issues.push('属性所属类不存在。')
    const slot = JSON.stringify([item.conceptId, item.name])
    if (attributes.has(slot)) issues.push('同一类不能有重名属性。')
    attributes.add(slot)
    if (!['string', 'integer', 'decimal', 'boolean', 'date', 'datetime'].includes(item.datatype)) issues.push('属性数据类型不受支持。')
  }
  const relations = new Set<string>()
  for (const relation of draft.relations) {
    if (!validText(relation.name)) issues.push('关系名称不能为空、过长或包含控制字符。')
    if (!ids.has(relation.sourceId) || !ids.has(relation.targetId)) issues.push('关系端点必须引用当前本体中的类。')
    if (!['unknown', 'one-to-one', 'one-to-many', 'many-to-one', 'many-to-many'].includes(relation.cardinality)) issues.push('关系基数不受支持。')
    const identity = JSON.stringify([relation.name, relation.sourceId, relation.targetId])
    if (relations.has(identity)) issues.push('同一起点与终点不能有重名关系。')
    relations.add(identity)
  }
  return [...new Set(issues)]
}

export function initialWorkspace(): WorkspaceState {
  return { materials: [], selected: [], draft: null, validation: null, active: null, error: '', notice: '' }
}

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  const base = { ...state, error: '', notice: '' }
  switch (action.type) {
    case 'add-materials':
      return { ...base, materials: [...state.materials, ...action.materials],
        selected: [...state.selected, ...action.materials.map(item => item.id)], notice: '材料已读取，保存后参与服务端建模。' }
    case 'toggle-material':
      return { ...base, selected: state.selected.includes(action.id) ? state.selected.filter(id => id !== action.id) : [...state.selected, action.id] }
    case 'edit-class':
    case 'edit-property':
    case 'edit-relation': {
      if (!state.draft) return state
      const draft = structuredClone(state.draft)
      if (action.type === 'edit-class') {
        const value = action.value
        const cls = draft.classes.find(item => item.id === value.id)
        if (!cls) return { ...base, error: '类不存在，请重新选择。' }
        Object.assign(cls, { name: value.name.trim(), aliases: value.aliases.map(alias => alias.trim()).filter(Boolean),
          description: value.description, parentId: action.value.parentId, edited: true })
        draft.items = draft.items.map(item => item.conceptId === cls.id ? { ...item, concept: cls.name } : item)
      } else if (action.type === 'edit-property') {
        const value = action.value
        const item = draft.items.find(item => item.id === value.id)
        if (!item) return { ...base, error: '属性不存在，请重新选择。' }
        Object.assign(item, { name: value.name.trim(), aliases: value.aliases.map(alias => alias.trim()).filter(Boolean),
          description: value.description, conceptId: action.value.conceptId, datatype: action.value.datatype, unit: action.value.unit,
          concept: draft.classes.find(cls => cls.id === action.value.conceptId)?.name ?? item.concept, edited: true })
      } else {
        const value = action.value
        const relation = draft.relations.find(item => item.id === value.id)
        if (!relation) return { ...base, error: '关系不存在，请重新选择。' }
        Object.assign(relation, { name: value.name.trim(), description: value.description, sourceId: action.value.sourceId,
          targetId: action.value.targetId, cardinality: action.value.cardinality, symmetric: action.value.symmetric,
          transitive: action.value.transitive, functional: action.value.functional, edited: true })
      }
      const issues = ontologyIssues(draft)
      if (issues.length) return { ...base, error: issues.join(' ') }
      return { ...base, draft: { ...draft, revision: draft.revision + 1 }, validation: null,
        notice: '本体修改已保存到当前草稿；请重新检查。已采用版本和历史回答保持原样。' }
    }
    case 'exclude':
      if (!state.draft) return state
      return { ...base, draft: { ...state.draft, revision: state.draft.revision + 1, items: state.draft.items.map(item =>
        item.id === action.id ? { ...item, excluded: action.excluded } : item) }, validation: null }
    case 'validate':
    case 'adopt':
      return { ...base, error: '请使用服务端草稿执行校验和采用。' }
    case 'clear-message':
      return base
  }
}
