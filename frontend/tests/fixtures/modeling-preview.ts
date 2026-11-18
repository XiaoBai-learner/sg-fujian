/** Isolated interaction fixtures. Never send these results to the formal modeling API. */
export type Material = {
  id: string; name: string; kind: 'DDL' | '热点 SQL' | '任务 SQL' | '业务说明' | 'PDF'
  origin: 'example' | 'upload'; body: string; size: number; remoteRevision?: number
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
  field: string; status: 'located' | 'not_found' | 'no_model'; kind?: Candidate['kind']
  sources: string[]; item?: Candidate
}
export type ValidationCase = { field: string; expected: string[]; actual: string[]; passed: boolean; skipped: boolean; note: string }
export type PreviewState = {
  live?: { runId: string; stats: Record<string, number>; diagnostics: {code: string; message: string}[]; method: string; check: import('./live').LiveRun['validation'] };
  materials: Material[]; selected: string[]
  draft: OntologyDraft | null
  validation: { revision: number; cases: ValidationCase[] } | null
  active: Snapshot | null; error: string; notice: string
}
export type PreviewAction =
  | { type: 'load-example' } | { type: 'add-materials'; materials: Material[] }
  | { type: 'toggle-material'; id: string } | { type: 'generate' }
  | { type: 'exclude'; id: string; excluded: boolean }
  | { type: 'edit-class'; value: OntologyClass } | { type: 'edit-property'; value: Candidate }
  | { type: 'edit-relation'; value: OntologyRelation }
  | { type: 'validate' } | { type: 'adopt' } | { type: 'clear-message' }

const examples: Material[] = [
  { id: 'example-ddl', name: '营销系统结构.sql', kind: 'DDL', origin: 'example', size: 0, body:
`-- 合成材料，仅用于交互预览；不来自客户系统。
CREATE TABLE yx186.C_CONS (
  CONS_ID BIGINT NOT NULL PRIMARY KEY COMMENT '客户内部标识',
  CONS_NO VARCHAR(32) NOT NULL COMMENT '户号',
  CONS_NAME VARCHAR(128) COMMENT '用户名称',
  MOBILE VARCHAR(32) COMMENT '客户联系电话'
) COMMENT='用电客户';
CREATE TABLE yx186.A_RCVBL_FLOW (
  FLOW_ID BIGINT NOT NULL PRIMARY KEY,
  CONS_ID BIGINT NOT NULL COMMENT '客户内部标识',
  RCVBL_AMT DECIMAL(18,2) COMMENT '应收金额，元',
  RCVED_AMT DECIMAL(18,2) COMMENT '已收金额，元',
  BILL_YM CHAR(6) COMMENT '账务年月',
  FOREIGN KEY (CONS_ID) REFERENCES yx186.C_CONS(CONS_ID)
) COMMENT='电费应收记录';
CREATE TABLE yx186.C_CONTACT (
  CONTACT_ID BIGINT NOT NULL PRIMARY KEY,
  CONS_ID BIGINT NOT NULL,
  PHONE VARCHAR(32) COMMENT '业务联系人电话'
);` },
  { id: 'example-sql', name: '常用取数查询.sql', kind: '热点 SQL', origin: 'example', size: 0, body:
`-- 合成查询模板。频率只用于排序，不能证明业务语义。
-- 模板 A：调用 42 次
SELECT c.CONS_NO AS 户号, c.CONS_NAME AS 用户名称,
       b.RCVBL_AMT AS 应收金额
FROM yx186.C_CONS c
JOIN yx186.A_RCVBL_FLOW b ON c.CONS_ID = b.CONS_ID;

-- 模板 B：调用 18 次
SELECT c.CONS_NO AS 户号,
       SUM(b.RCVBL_AMT - b.RCVED_AMT) AS 欠费金额
FROM yx186.C_CONS c
JOIN yx186.A_RCVBL_FLOW b ON c.CONS_ID = b.CONS_ID
WHERE b.BILL_YM = :账务年月 AND b.RCVBL_AMT > b.RCVED_AMT
GROUP BY c.CONS_NO;

-- 模板 C：调用 7 次；名称相同，业务对象不同，保留歧义
SELECT c.MOBILE AS 联系电话 FROM yx186.C_CONS c;
SELECT p.PHONE AS 联系电话 FROM yx186.C_CONTACT p;` },
  { id: 'example-doc', name: '字段与口径说明.md', kind: '业务说明', origin: 'example', size: 0, body:
`# 合成字段说明
户号是用电客户的业务编号，对应 C_CONS.CONS_NO；客户内部标识不作为户号。
用户名称对应 C_CONS.CONS_NAME，页面也称客户名称。
应收金额以元为单位，来源是电费应收记录的 RCVBL_AMT。
本示例的欠费金额按户号、指定账务年月汇总应收金额减已收金额，只统计未收清的记录。
“联系电话”可能是客户本人电话，也可能是业务联系人电话，需要补充页面上下文。
这些定义仅用于演示，不能推广为福建营销域的真实业务口径。` },
].map(item => ({ ...item, size: new TextEncoder().encode(item.body).length })) as Material[]

function exampleCandidates(): Candidate[] {
  return [
    { id: 'cons-no', name: '户号', aliases: ['客户户号'], concept: '用电客户', description: '用电客户的业务编号，与内部主键分开建模。',
      conceptId: 'customer', datatype: 'string', unit: '', kind: 'direct', sources: ['yx186.C_CONS.CONS_NO'], evidence: [
        { materialId: 'example-ddl', label: '字段注释', quote: "CONS_NO VARCHAR(32) NOT NULL COMMENT '户号'" },
        { materialId: 'example-sql', label: '查询别名', quote: 'c.CONS_NO AS 户号' },
        { materialId: 'example-doc', label: '业务说明', quote: '户号是用电客户的业务编号，对应 C_CONS.CONS_NO；客户内部标识不作为户号。' },
      ] },
    { id: 'cons-name', name: '用户名称', aliases: ['客户名称'], concept: '用电客户', description: '保留“客户名称”的页面叫法，映射到同一个本体属性。',
      conceptId: 'customer', datatype: 'string', unit: '', kind: 'direct', sources: ['yx186.C_CONS.CONS_NAME'], evidence: [
        { materialId: 'example-ddl', label: '字段注释', quote: "CONS_NAME VARCHAR(128) COMMENT '用户名称'" },
        { materialId: 'example-doc', label: '同义叫法', quote: '用户名称对应 C_CONS.CONS_NAME，页面也称客户名称。' },
      ] },
    { id: 'receivable', name: '应收金额', aliases: [], concept: '电费应收记录', description: '应收记录上的直接金额属性，单位为元。',
      conceptId: 'receivable-record', datatype: 'decimal', unit: '元', kind: 'direct', sources: ['yx186.A_RCVBL_FLOW.RCVBL_AMT'], evidence: [
        { materialId: 'example-ddl', label: '类型与单位', quote: "RCVBL_AMT DECIMAL(18,2) COMMENT '应收金额，元'" },
        { materialId: 'example-sql', label: '查询投影', quote: 'b.RCVBL_AMT AS 应收金额' },
      ] },
    { id: 'arrears', name: '欠费金额', aliases: [], concept: '电费应收记录', description: '保留计算依赖、过滤条件与粒度，不伪装成单一物理列。',
      conceptId: 'receivable-record', datatype: 'decimal', unit: '元', kind: 'calculated', sources: ['yx186.A_RCVBL_FLOW.RCVBL_AMT', 'yx186.A_RCVBL_FLOW.RCVED_AMT'],
      expression: 'SUM(RCVBL_AMT - RCVED_AMT)',
      scope: '按户号、指定账务年月汇总；仅包含应收金额大于已收金额的记录；单位：元。',
      evidence: [
        { materialId: 'example-sql', label: '计算表达式', quote: 'SUM(b.RCVBL_AMT - b.RCVED_AMT) AS 欠费金额' },
        { materialId: 'example-sql', label: '过滤与粒度', quote: 'WHERE b.BILL_YM = :账务年月 AND b.RCVBL_AMT > b.RCVED_AMT\nGROUP BY c.CONS_NO;' },
        { materialId: 'example-doc', label: '口径说明', quote: '本示例的欠费金额按户号、指定账务年月汇总应收金额减已收金额，只统计未收清的记录。' },
      ] },
    { id: 'phone', name: '联系电话', aliases: [], concept: '客户 / 业务联系人', description: '同名字段属于不同对象。需要补充业务页面或文档才能确定。',
      conceptId: null, datatype: 'string', unit: '', kind: 'direct', sources: ['yx186.C_CONS.MOBILE', 'yx186.C_CONTACT.PHONE'], uncertain: true, evidence: [
        { materialId: 'example-sql', label: '存在两个来源', quote: 'SELECT c.MOBILE AS 联系电话 FROM yx186.C_CONS c;\nSELECT p.PHONE AS 联系电话 FROM yx186.C_CONTACT p;' },
      ] },
  ]
}

function exampleOntology(): Pick<OntologyDraft, 'classes' | 'relations'> {
  return {
    classes: [
      { id: 'customer', name: '用电客户', aliases: ['客户'], description: '营销系统中的用电客户；业务编号与内部主键分开表达。', parentId: null,
        evidence: [{ materialId: 'example-ddl', label: '表注释', quote: ") COMMENT='用电客户';" }] },
      { id: 'receivable-record', name: '电费应收记录', aliases: ['应收记录'], description: '记录账务年月对应的应收、已收金额，按客户关联。', parentId: null,
        evidence: [{ materialId: 'example-ddl', label: '表注释', quote: ") COMMENT='电费应收记录';" }] },
      { id: 'contact', name: '业务联系人', aliases: [], description: 'C_CONTACT 中记录的联系人。电话与客户本人电话不可直接等同。', parentId: null,
        evidence: [{ materialId: 'example-ddl', label: '字段注释', quote: "PHONE VARCHAR(32) COMMENT '业务联系人电话'" }] },
    ],
    relations: [
      { id: 'customer-bills', name: '关联应收记录', description: '由 CONS_ID 外键与查询 JOIN 支持的结构关联；业务命名仍需核对。',
        sourceId: 'customer', targetId: 'receivable-record', cardinality: 'one-to-many', symmetric: false, transitive: false, functional: false,
        evidence: [{ materialId: 'example-ddl', label: '外键', quote: 'FOREIGN KEY (CONS_ID) REFERENCES yx186.C_CONS(CONS_ID)' },
          { materialId: 'example-sql', label: '查询关联', quote: 'JOIN yx186.A_RCVBL_FLOW b ON c.CONS_ID = b.CONS_ID;' }] },
      { id: 'customer-contact', name: '候选联系人关联', description: 'C_CONTACT 中有 CONS_ID，但本示例没有显式外键或 JOIN；仅是待核对的关联候选。',
        sourceId: 'customer', targetId: 'contact', cardinality: 'unknown', symmetric: false, transitive: false, functional: false, uncertain: true,
        evidence: [{ materialId: 'example-ddl', label: '同名列线索，尚非关联证明', quote:
          "CREATE TABLE yx186.C_CONTACT (\n  CONTACT_ID BIGINT NOT NULL PRIMARY KEY,\n  CONS_ID BIGINT NOT NULL,\n  PHONE VARCHAR(32) COMMENT '业务联系人电话'\n);" }] },
    ],
  }
}

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

export function initialPreview(): PreviewState {
  return { materials: [], selected: [], draft: null, validation: null, active: null, error: '', notice: '' }
}

export function tracePreview(snapshot: Snapshot | null, field: string): TraceResult {
  if (!snapshot) return { field, status: 'no_model', sources: [] }
  const matches = snapshot.items.filter(item => !item.uncertain && !item.excluded &&
    [item.name, ...item.aliases].includes(field.trim()))
  const item = matches.length === 1 ? matches[0] : null
  return item ? { field, status: 'located', kind: item.kind, sources: [...item.sources], item }
    : { field, status: 'not_found', sources: [] }
}

export function previewReducer(state: PreviewState, action: PreviewAction): PreviewState {
  const base = { ...state, error: '', notice: '' }
  switch (action.type) {
    case 'load-example':
      return { ...base, materials: [...state.materials.filter(item => item.origin !== 'example'), ...structuredClone(examples)],
        selected: examples.map(item => item.id), draft: null, validation: null, notice: '已载入合成示例材料，可以体验完整流程。' }
    case 'add-materials':
      return { ...base, materials: [...state.materials, ...action.materials],
        selected: [...state.selected, ...action.materials.map(item => item.id)], draft: null, validation: null,
        notice: '材料已在本次页面中读取。自定义材料的后端解析与识别尚未接通。' }
    case 'toggle-material':
      return { ...base, selected: state.selected.includes(action.id) ? state.selected.filter(id => id !== action.id) : [...state.selected, action.id],
        draft: null, validation: null }
    case 'generate':
      if (state.selected.length !== examples.length || examples.some(item => !state.selected.includes(item.id)))
        return { ...base, draft: null, validation: null, error: '识别服务尚未接通。自定义材料只能预览；请选用完整合成示例体验生成流程。' }
      return { ...base, draft: { revision: 1, items: exampleCandidates(), ...exampleOntology() }, validation: null,
        notice: '已载入示例分析结果。4 个字段具备来源依据，1 个字段需要补充上下文。' }
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
    case 'validate': {
      if (!state.draft) return state
      const issues = ontologyIssues(state.draft)
      if (issues.length) return { ...base, validation: null, error: issues.join(' ') }
      const snapshot = { version: 0, ...state.draft }
      // Independent hand-checked fixture answers; not inputs to exampleCandidates.
      const gold = [
        { field: '户号', expected: ['yx186.C_CONS.CONS_NO'], note: '业务编号不能误映射到 CONS_ID。' },
        { field: '客户名称', expected: ['yx186.C_CONS.CONS_NAME'], note: '未使用主显示名，检验同义叫法。' },
        { field: '应收金额', expected: ['yx186.A_RCVBL_FLOW.RCVBL_AMT'], note: '检验直接字段映射。' },
        { field: '欠费金额', expected: ['yx186.A_RCVBL_FLOW.RCVBL_AMT', 'yx186.A_RCVBL_FLOW.RCVED_AMT'], note: '检验计算字段的完整依赖列。' },
        { field: '联系电话', expected: [], note: '来源有歧义，应暂不纳入可用模型。' },
      ]
      const cases = gold.map(item => {
        const actual = tracePreview(snapshot, item.field).sources
        const skipped = state.draft!.items.some(candidate => candidate.excluded &&
          [candidate.name, ...candidate.aliases].includes(item.field))
        return { ...item, actual, skipped,
          passed: !skipped && JSON.stringify([...actual].sort()) === JSON.stringify([...item.expected].sort()) }
      })
      return { ...base, validation: { revision: state.draft.revision, cases },
        notice: '示例来源检查已完成。此检查不代表真实识别准确率或业务口径已验证。' }
    }
    case 'adopt':
      if (!state.draft || !state.validation || state.validation.revision !== state.draft.revision ||
        !state.validation.cases.every(item => item.passed || item.skipped) ||
        !state.draft.items.some(item => !item.uncertain && !item.excluded) || ontologyIssues(state.draft).length > 0)
        return { ...base, error: '请先检查当前草稿；仅检查通过的当前版本可以用于示例溯源。' }
      return { ...base, active: { version: (state.active?.version ?? 0) + 1,
        items: structuredClone(state.draft.items.filter(item => !item.uncertain && !item.excluded)),
        classes: structuredClone(state.draft.classes), relations: structuredClone(state.draft.relations.filter(item => !item.uncertain)) },
        notice: '已采用示例模型，智能体现在可以使用此版本。待确认项不进入当前版本。' }
    case 'clear-message':
      return base
  }
}
