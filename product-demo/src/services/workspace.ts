import type { Editors, Result, Workspace } from '../domain/types.ts'
import { editors, sources } from './seed.ts'

export function initialWorkspace(): Workspace {
  return {
    sources: structuredClone(sources),
    materials: [
      { id: 'ddl', name: '营销系统结构.sql', kind: 'DDL', size: 4280 },
      { id: 'sql', name: '客户欠费汇总.sql', kind: '任务 SQL', size: 1620 },
    ],
    editors: structuredClone(editors), revision: 1,
    active: { revision: 1, editors: structuredClone(editors) }, turns: [],
  }
}

export function checkModel(value: Editors): string[] {
  const issues: string[] = []
  const concepts = new Set(value.model.concepts.map(c => c.id))
  const attributes = new Set(value.model.attributes.map(a => a.id))
  if (!concepts.size) issues.push('请至少建立一个业务对象。')
  if (!value.pipeline.bindings.length) issues.push('请至少添加一个数据表绑定。')
  for (const binding of value.pipeline.bindings) {
    if (!concepts.has(binding.concept_id)) issues.push(`${binding.table_name} 的业务对象不存在。`)
    if (!binding.key_columns.length) issues.push(`${binding.table_name} 缺少实体键。`)
    for (const mapping of binding.attributes) {
      if (!attributes.has(mapping.attribute_id)) issues.push(`${mapping.column} 引用了不存在的属性。`)
      if (!mapping.column.trim()) issues.push(`${binding.table_name} 存在空字段映射。`)
    }
  }
  for (const attribute of value.model.attributes) {
    if (!attribute.name.trim()) issues.push('属性名称不能为空。')
    if (!concepts.has(attribute.concept_id)) issues.push(`${attribute.name} 所属对象不存在。`)
  }
  return issues
}

export function activateModel(state: Workspace): Workspace {
  const issues = checkModel(state.editors)
  if (issues.length) throw new Error(issues.join('\n'))
  return { ...state, active: { revision: state.revision, editors: structuredClone(state.editors) } }
}

export function traceFields(state: Workspace, labels: string[]): Result[] {
  // shortcut: 原型通过已应用编辑器快照模拟本体/R2RML 检索；接入后端时替换为 TTL SemanticIndex。
  const { model, pipeline, rules } = state.active.editors
  const normalize = (text: string) => text.trim().replace(/[?？。]/g, '')
  const sourceFor = (attributeId: string) => pipeline.bindings.flatMap(binding => binding.attributes
    .filter(mapping => mapping.attribute_id === attributeId).map(mapping => ({
      column: `${binding.schema_name}.${binding.table_name}.${mapping.column}`,
      label: model.attributes.find(a => a.id === attributeId)?.name || attributeId,
      concept: String(model.concepts.find(c => c.id === binding.concept_id)?.name || binding.concept_id),
    })))
  return labels.slice(0, 40).map(label => {
    const result: Result = { label, status: 'not_found', kind: 'direct', sources: [], evidence: [] }
    const attributes = model.attributes.filter(a => [a.name, ...(a.aliases || [])].some(name => normalize(name) === normalize(label)))
    result.sources = attributes.flatMap(a => sourceFor(a.id))
    if (result.sources.length) {
      result.status = result.sources.length === 1 ? 'located' : 'ambiguous'
      result.evidence = attributes.map(a => `本体属性「${a.name}」→ 数据表绑定 → 物理列（模型 v${state.active.revision}）`)
      return result
    }
    for (const annotation of model.annotations.filter(a => a.key === 'demo:calculation')) {
      try {
        const calc = JSON.parse(String(annotation.value))
        if (calc.label !== normalize(label)) continue
        const inputs = calc.inputs as string[]
        if (!inputs.every(id => sourceFor(id).length > 0)) continue
        return { ...result, status: 'located', kind: 'calculated', sources: inputs.flatMap(sourceFor),
          calculation: { formula: calc.formula, filters: calc.filters },
          evidence: ['当前应用模型中的计算口径', '输入属性经映射指向物理列'] } as Result
      } catch { continue }
    }
    const rule = rules.rules.find(rule => rule.enabled && [String(rule.name), String(model.concepts.find(c => c.id === (rule.head as { predicate: string })?.predicate)?.name || '')].includes(normalize(label)))
    if (rule) return { ...result, kind: 'rule', status: 'located', rule: String(rule.nl), evidence: [`规则「${rule.name}」`, '这是分类口径解释，未查询客户实例。'] } as Result
    result.evidence = ['当前本体和映射没有覆盖这个字段，可补充页面上下文或到本体建模中维护。']
    return result
  })
}

export function extractFields(question: string, ocr: string, state: Workspace): string[] {
  const quoted = [...question.matchAll(/[“「"']([^”」"']+)[”」"']/g)].map(match => match[1])
  if (quoted.length) return [...new Set(quoted)]
  const names = [...new Set([
    ...state.active.editors.model.attributes.flatMap(a => [a.name, ...(a.aliases || [])]),
    '欠费金额', ...state.active.editors.model.concepts.map(c => String(c.name)),
  ])].sort((a, b) => b.length - a.length)
  const explicit = names.filter(name => question.includes(name))
  if (explicit.length) return explicit.filter(name => !explicit.some(other => other !== name && other.includes(name)))
  if (ocr.trim()) {
    const header = ocr.split('\n').find(line => line.trim().split(/\s{2,}|\t|\|/).filter(Boolean).length >= 2)
    if (header) return header.split(/\s{2,}|\t|\|/).map(s => s.trim()).filter(Boolean).slice(0, 40)
  }
  return question.split(/[、,，;；\n]/).map(s => s.trim().replace(/(来自哪里|来自哪个字段|属于什么表|是什么|怎么认定的|[？?])/g, '')).filter(Boolean).slice(0, 40)
}
