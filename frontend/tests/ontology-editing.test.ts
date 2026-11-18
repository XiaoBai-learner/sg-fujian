import test from 'node:test'
import assert from 'node:assert/strict'
import { initialPreview, previewReducer, tracePreview } from './fixtures/modeling-preview.ts'

const prepared = () => previewReducer(previewReducer(initialPreview(), { type: 'load-example' }), { type: 'generate' })

test('class renaming retains IDs and updates property labels without rewriting physical mappings', () => {
  let state = prepared()
  const cls = state.draft!.classes.find(item => item.id === 'customer')!
  state = previewReducer(state, { type: 'edit-class', value: { ...cls, name: '电力客户', aliases: ['用电客户'] } })
  assert.equal(state.draft!.classes.find(item => item.id === 'customer')?.name, '电力客户')
  assert.equal(state.draft!.items.find(item => item.id === 'cons-no')?.concept, '电力客户')
  assert.deepEqual(state.draft!.items.find(item => item.id === 'cons-no')?.sources, ['yx186.C_CONS.CONS_NO'])
  assert.equal(state.draft!.relations.find(item => item.id === 'customer-bills')?.sourceId, 'customer')
})

test('editing relationships saves direction, endpoints and cardinality and invalidates checks only on the draft', () => {
  let state = previewReducer(previewReducer(prepared(), { type: 'validate' }), { type: 'adopt' })
  const relation = state.draft!.relations.find(item => item.id === 'customer-bills')!
  state = previewReducer(state, { type: 'edit-relation', value: {
    ...relation, name: '归属客户', sourceId: 'receivable-record', targetId: 'customer', cardinality: 'many-to-one',
  } })
  assert.equal(state.error, '')
  assert.equal(state.validation, null)
  assert.equal(state.draft!.relations.find(item => item.id === relation.id)?.sourceId, 'receivable-record')
  assert.equal(state.draft!.relations.find(item => item.id === relation.id)?.cardinality, 'many-to-one')
  assert.equal(state.active!.relations.find(item => item.id === relation.id)?.sourceId, 'customer')
})

test('property edits synchronize tracing labels only after adoption, keeping historical snapshots intact', () => {
  let state = previewReducer(previewReducer(prepared(), { type: 'validate' }), { type: 'adopt' })
  const property = state.draft!.items.find(item => item.id === 'cons-no')!
  state = previewReducer(state, { type: 'edit-property', value: { ...property, name: '供电户号', aliases: ['户号', '客户户号'] } })
  assert.equal(state.validation, null)
  assert.equal(tracePreview(state.active, '供电户号').status, 'not_found')
  state = previewReducer(previewReducer(state, { type: 'validate' }), { type: 'adopt' })
  assert.equal(tracePreview(state.active, '供电户号').status, 'located')
  assert.equal(tracePreview(state.active, '户号').status, 'located')
})

test('dangling relation endpoints and inheritance cycles cannot enter the draft', () => {
  const state = prepared()
  const relation = state.draft!.relations[0]
  const invalid = previewReducer(state, { type: 'edit-relation', value: { ...relation, targetId: 'missing' } })
  assert.match(invalid.error, /关系端点/)
  assert.equal(invalid.draft, state.draft)
  const customer = state.draft!.classes.find(item => item.id === 'customer')!
  const bills = state.draft!.classes.find(item => item.id === 'receivable-record')!
  const first = previewReducer(state, { type: 'edit-class', value: { ...customer, parentId: bills.id } })
  const cyclic = previewReducer(first, { type: 'edit-class', value: { ...bills, parentId: customer.id } })
  assert.match(cyclic.error, /循环/)
  assert.equal(cyclic.draft, first.draft)
})

test('duplicate property names within a class are rejected, and merely editing ambiguity does not resolve it', () => {
  const state = prepared()
  const property = state.draft!.items.find(item => item.id === 'cons-no')!
  const duplicate = previewReducer(state, { type: 'edit-property', value: { ...property, name: '用户名称' } })
  assert.match(duplicate.error, /同一类/)
  const ambiguous = state.draft!.items.find(item => item.id === 'phone')!
  const edited = previewReducer(state, { type: 'edit-property', value: { ...ambiguous, name: '联系人电话', conceptId: 'contact' } })
  assert.equal(edited.draft!.items.find(item => item.id === 'phone')?.uncertain, true)
})

test('semantic edits cannot silently alter source evidence and mapping', () => {
  const state = prepared()
  const property = state.draft!.items[0]
  const edited = previewReducer(state, { type: 'edit-property', value: { ...property, name: '新名称', sources: ['wrong.table.column'], evidence: [] } })
  assert.deepEqual(edited.draft!.items[0].sources, ['yx186.C_CONS.CONS_NO'])
  assert.deepEqual(edited.draft!.items[0].evidence, property.evidence)
})

test('all class and relation evidence remains locatable, and uncertain relations stay outside adoption', () => {
  const state = prepared()
  for (const item of [...state.draft!.classes, ...state.draft!.relations]) {
    for (const evidence of item.evidence) {
      assert.ok(state.materials.find(material => material.id === evidence.materialId)?.body.includes(evidence.quote))
    }
  }
  const adopted = previewReducer(previewReducer(state, { type: 'validate' }), { type: 'adopt' })
  assert.deepEqual(adopted.active!.relations.map(item => item.id), ['customer-bills'])
  assert.equal(state.draft!.relations.length, 2)
})
