import type { Editors, Material, Model, Source, Workspace } from '../domain/types.ts'
import { editors as vocabulary, materials as examples, reference } from './seed.ts'

export interface SchemaTable { schema: string; table: Source['tables'][number]; sourceId: string }
export interface ModelingInput { id: string; name: string; kind: string; ready: boolean; text: string; tables: SchemaTable[] }
export interface ModelPreview { base: string; inputIds: string[]; model: Model; bindings: Editors['pipeline']['bindings']; tables: SchemaTable[]; warnings: string[] }

export function collectModelingInputs(state: Workspace): ModelingInput[] {
  return [
    ...state.sources.map(source => ({
      id: `source:${source.id}`, name: `${source.name} · ${source.database}`, kind: '结构快照', ready: source.tables.length > 0,
      text: source.tables.map(table => `${source.database}.${table.name} ${table.label}\n${table.columns.map(column => `${column.name} ${column.data_type} ${column.label}`).join('\n')}`).join('\n\n'),
      tables: source.tables.map(table => ({ schema: source.database, table, sourceId: source.id })),
    })),
    ...state.materials.map(material => ({
      id: `material:${material.id}`, name: material.name, kind: material.kind,
      ready: Boolean((material.text ?? examples.find(example => example.id === material.id && example.name === material.name)?.text)?.trim()),
      text: material.text ?? examples.find(example => example.id === material.id && example.name === material.name)?.text ?? '', tables: [],
    })),
  ]
}

export async function readModelingFiles(files: File[]): Promise<Material[]> {
  return Promise.all(files.map(async file => {
    if (!/\.(txt|md|sql|pdf|csv|json)$/i.test(file.name)) throw new Error(`${file.name}：支持 TXT、Markdown、SQL、PDF、CSV 和 JSON。`)
    if (file.size > 1024 * 1024) throw new Error(`${file.name}：本地预览每份材料最多 1 MB。`)
    const pdf = /\.pdf$/i.test(file.name)
    const text = pdf ? undefined : await file.text()
    if (text?.includes('\0') || text?.includes('\uFFFD')) throw new Error(`${file.name}：请使用 UTF-8 文本。`)
    return { id: crypto.randomUUID(), name: file.name, kind: /\.sql$/i.test(file.name) ? 'DDL' : '业务说明', size: file.size, text }
  }))
}

// shortcut: 只为前端预览解析基本 CREATE TABLE；正式方言解析由后端 sqlglot 完成。
function sqlParts(text: string, separator: string): string[] {
  const parts: string[] = []
  let part = '', quote = '', depth = 0
  for (let i = 0; i < text.length; i++) {
    const char = text[i], next = text[i + 1]
    if (quote) {
      part += char
      if (char === '\\' || (char === quote && next === quote)) { part += next || ''; i++ }
      else if (char === quote) quote = ''
      continue
    }
    if (char === '-' && next === '-') { while (i < text.length && text[i] !== '\n') i++; part += '\n'; continue }
    if (char === '/' && next === '*') {
      const end = text.indexOf('*/', i + 2)
      if (end < 0) throw new Error('DDL 注释未闭合。')
      i = end + 1; part += ' '; continue
    }
    if ("'\"`".includes(char)) quote = char
    if (char === '(') depth++
    if (char === ')') depth--
    if (char === separator && depth === 0) { if (part.trim()) parts.push(part.trim()); part = '' }
    else part += char
  }
  if (quote || depth !== 0) throw new Error('DDL 中的引号或括号未闭合，请检查文件。')
  if (part.trim()) parts.push(part.trim())
  return parts
}

const unquote = (name: string) => name.trim().replace(/[`"]/g, '')
const datatype = (type: string) => /int|number\(.*,\s*0\)/i.test(type) ? 'integer'
  : /decimal|numeric|number|float|double|real/i.test(type) ? 'decimal'
    : /datetime|timestamp/i.test(type) ? 'dateTime' : /date/i.test(type) ? 'date' : /bool/i.test(type) ? 'boolean' : 'string'

function ddlTables(text: string, sourceId: string): SchemaTable[] {
  const tables: SchemaTable[] = []
  let database = ''
  for (const statement of sqlParts(text, ';')) {
    const use = statement.match(/^USE\s+([`"\w$]+)$/i)
    if (use) { database = unquote(use[1]); continue }
    const match = statement.match(/^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\w$]+(?:\s*\.\s*[`"\w$]+)?)\s*\(([\s\S]*)\)\s*([^;]*)$/i)
    if (!match) continue
    const names = match[1].split('.').map(unquote)
    const columns: Source['tables'][number]['columns'] = [], keys: string[] = []
    for (const definition of sqlParts(match[2], ',')) {
      const key = definition.match(/(?:^|\s)PRIMARY\s+KEY\s*\(([^)]+)\)/i)
      if (key) keys.push(...key[1].split(',').map(unquote))
      if (/^(PRIMARY|FOREIGN|CONSTRAINT|UNIQUE|KEY|CHECK|INDEX)\b/i.test(definition)) continue
      const column = definition.match(/^([`"\w$]+)\s+([a-zA-Z]+)([\s\S]*)$/)
      if (!column) throw new Error('此 DDL 暂不能生成本地预览，请保留材料等待后端解析。')
      const name = unquote(column[1])
      if (/\bPRIMARY\s+KEY\b/i.test(column[3])) keys.push(name)
      columns.push({ name, label: column[3].match(/\bCOMMENT\s+'((?:[^']|'')*)'/i)?.[1].replace(/''/g, "'") || name,
        data_type: datatype(column[2]), nullable: !/\bNOT\s+NULL\b/i.test(column[3]), primary_key: false, position: columns.length })
    }
    for (const column of columns) if (keys.includes(column.name)) { column.primary_key = true; column.nullable = false }
    const schema = names.length > 1 ? names[0] : database
    if (columns.length) tables.push({ schema, sourceId: `${sourceId}:${schema}`,
      table: { name: names.at(-1)!, label: match[3].match(/\bCOMMENT\s*=?\s*'((?:[^']|'')*)'/i)?.[1].replace(/''/g, "'") || names.at(-1)!, columns } })
  }
  return tables
}

export function generateModelPreview(state: Workspace, inputIds: string[]): ModelPreview {
  if (!inputIds.length) throw new Error('请至少选择一份建模材料。')
  const available = collectModelingInputs(state), inputs = inputIds.map(id => available.find(input => input.id === id))
  if (inputs.some(input => !input?.ready)) throw new Error('所选材料缺少正文或尚待解析，请先核对材料。')
  const model: Model = { format_version: 'wing-model-editor/1', concepts: [], attributes: [], relations: [], annotations: [] }
  const bindings: ModelPreview['bindings'] = [], warnings: string[] = [], previewTables: SchemaTable[] = []
  const seen = new Set<string>()
  for (const input of inputs as ModelingInput[]) {
    const tables = input.tables.length ? input.tables : input.kind === 'DDL' ? ddlTables(input.text, input.id) : []
    for (const { schema, table, sourceId } of tables) {
      const identity = `${schema}.${table.name}`
      if (seen.has(identity)) {
        const binding = bindings.find(binding => binding.schema_name === schema && binding.table_name === table.name)
        if (binding) model.annotations.push({ subject: binding.concept_id, key: 'demo:material', value: input.name })
        continue
      }
      seen.add(identity)
      previewTables.push({ schema, table: structuredClone(table), sourceId })
      const existing = state.editors.pipeline.bindings.find(binding => binding.schema_name === schema && binding.table_name === table.name)
      const conceptId = existing?.concept_id || `table_${encodeURIComponent(identity)}`
      const concept = state.editors.model.concepts.find(concept => concept.id === conceptId)
      model.concepts.push(concept ? structuredClone(concept) : { id: conceptId, name: table.label, english_name: table.name, parents: [], disjoint_with: [], description: `来源：${input.name} · ${identity}` })
      const mappings = table.columns.map(column => {
        const currentId = existing?.attributes.find(mapping => mapping.column === column.name)?.attribute_id
        const attribute = state.editors.model.attributes.find(attribute => attribute.id === currentId)
        const id = currentId || `${conceptId}_${column.name}`
        model.attributes.push(attribute ? structuredClone(attribute) : { id, name: column.label, concept_id: conceptId, datatype: datatype(column.data_type), aliases: [], sensitivity: 'internal' })
        return { attribute_id: id, column: column.name }
      })
      if (schema) bindings.push({ ...reference(schema, table.name, sourceId), id: existing?.id || `binding_${encodeURIComponent(identity)}`,
        concept_id: conceptId, identity_scope: conceptId, key_columns: table.columns.filter(column => column.primary_key).map(column => column.name), attributes: mappings, references: [] })
      else warnings.push(`${table.name} 未声明库名；先生成对象，需在 R2RML 中补充来源映射。`)
      model.annotations.push({ subject: conceptId, key: 'demo:material', value: input.name })
    }
    if (!tables.length && input.kind !== 'DDL') {
      // shortcut: 文档仅匹配营销域示例词汇，未知概念不编造；接入 OntoWing 后替换为真实识别。
      for (const concept of vocabulary.model.concepts) {
        const attributes = vocabulary.model.attributes.filter(attribute => attribute.concept_id === concept.id && [attribute.name, ...attribute.aliases].some(name => input.text.includes(name)))
        if (!input.text.includes(String(concept.name)) && !attributes.length) continue
        if (!model.concepts.some(item => item.id === concept.id)) model.concepts.push(structuredClone(concept))
        for (const attribute of attributes) if (!model.attributes.some(item => item.id === attribute.id)) model.attributes.push(structuredClone(attribute))
        model.annotations.push({ subject: concept.id, key: 'demo:material', value: input.name })
      }
    }
  }
  for (const relation of vocabulary.model.relations) {
    if (model.concepts.some(concept => concept.id === relation.source_id) && model.concepts.some(concept => concept.id === relation.target_id) &&
      inputs.some(input => input?.kind !== '结构快照' && input?.text.includes(String(relation.name)))) model.relations.push(structuredClone(relation))
  }
  if (!model.concepts.length) throw new Error('这些材料暂未产生本地预览。请使用基本 CREATE TABLE，或包含营销域对象和属性的文档；完整识别待接入 OntoWing 后执行。')
  return { base: JSON.stringify(state.editors), inputIds: [...inputIds], model, bindings, tables: previewTables, warnings }
}

export function adoptModelPreview(state: Workspace, preview: ModelPreview): Workspace {
  if (JSON.stringify(state.editors) !== preview.base) throw new Error('当前草稿已变化，请重新生成预览后再采用。')
  const next = structuredClone(state)
  const append = <T extends { id?: unknown }>(current: T[], incoming: T[]) => { for (const item of incoming) if (!current.some(value => value.id === item.id)) current.push(structuredClone(item)) }
  append(next.editors.model.concepts, preview.model.concepts)
  append(next.editors.model.attributes, preview.model.attributes)
  append(next.editors.model.relations, preview.model.relations)
  for (const annotation of preview.model.annotations) if (!next.editors.model.annotations.some(value => value.subject === annotation.subject && value.key === annotation.key && value.value === annotation.value)) next.editors.model.annotations.push(structuredClone(annotation))
  for (const { schema, table, sourceId } of preview.tables) {
    if (!schema || next.sources.some(source => source.database === schema && source.tables.some(current => current.name === table.name))) continue
    const current = next.sources.find(source => source.id === sourceId && source.database === schema)
    if (current) current.tables.push(structuredClone(table))
    else next.sources.push({ id: sourceId, name: `${schema} · DDL 导入`, type: 'DDL', host: '本地结构文件', database: schema, tables: [structuredClone(table)] })
  }
  for (const binding of preview.bindings) {
    const current = next.editors.pipeline.bindings.find(item => item.id === binding.id)
    if (!current) {
      next.editors.pipeline.bindings.push(structuredClone(binding))
      next.editors.pipeline.fact_planes.push(reference(binding.schema_name, binding.table_name, String(binding.data_source_id)))
    } else for (const mapping of binding.attributes) if (!current.attributes.some(item => item.column === mapping.column)) current.attributes.push(structuredClone(mapping))
  }
  if (next.revision === next.active.revision) next.revision++
  return next
}
