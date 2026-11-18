import test from 'node:test'
import assert from 'node:assert/strict'
import { initialPreview, previewReducer } from './fixtures/modeling-preview.ts'
import { layoutOntology, canvasScale } from '../src/modules/modeling/ontology-layout.ts'

test('fit bounds include self-relation labels on rightmost classes', () => {
  const state = previewReducer(previewReducer(initialPreview(), { type: 'load-example' }), { type: 'generate' })
  const draft = structuredClone(state.draft!)
  draft.relations[0].sourceId = 'receivable-record'
  draft.relations[0].targetId = 'receivable-record'
  const layout = layoutOntology(draft)
  // Right node x=545, width=240; loop label extends to x=972.
  assert.ok(layout.graphWidth >= 972 + 20)
  assert.equal(layout.positions.size, 3)
})

test('parallel and self-relations retain separate selectable labels', () => {
  const state = previewReducer(previewReducer(initialPreview(), { type: 'load-example' }), { type: 'generate' })
  const draft = structuredClone(state.draft!)
  draft.relations[1].targetId = 'receivable-record'
  let layout = layoutOntology(draft)
  assert.ok(Math.abs(layout.edges[0].labelY - layout.edges[1].labelY) >= 60)
  draft.relations.forEach(item => { item.sourceId = 'receivable-record'; item.targetId = 'receivable-record' })
  layout = layoutOntology(draft)
  assert.ok(Math.abs(layout.edges[0].labelX - layout.edges[1].labelX) >= 174)
  assert.ok(layout.graphWidth > Math.max(...layout.edges.map(item => item.labelX + 87)))
})

test('多行本体卡片按实际属性高度排布，不会压住下一行', () => {
  const base = previewReducer(previewReducer(initialPreview(), {type:'load-example'}), {type:'generate'}).draft!
  const draft = structuredClone(base)
  draft.classes = Array.from({length:6}, (_, i) => ({...base.classes[0], id:`class-${i}`, name:`类${i}`}))
  draft.items = draft.classes.flatMap(cls => Array.from({length:12}, (_, i) => ({...base.items[0], id:`${cls.id}-${i}`, conceptId:cls.id})))
  draft.relations = []
  const {positions} = layoutOntology(draft)
  const upper = positions.get('class-0')!, lower = positions.get('class-3')!
  assert.ok(lower.y >= upper.y + upper.height + 80, '两排卡片之间必须留出连线空间')
})

test('收起属性只简化画布，不改变本体数据和属性总数', () => {
  const draft = previewReducer(previewReducer(initialPreview(), {type:'load-example'}), {type:'generate'}).draft!
  const before = JSON.stringify(draft)
  const expanded = layoutOntology(draft)
  const compact = layoutOntology(draft, {showProperties:false})
  for (const cls of draft.classes) {
    assert.equal(compact.positions.get(cls.id)!.attributes.length, 0)
    assert.equal(compact.positions.get(cls.id)!.propertyCount, expanded.positions.get(cls.id)!.attributes.length)
    assert.ok(compact.positions.get(cls.id)!.height < expanded.positions.get(cls.id)!.height)
  }
  assert.equal(JSON.stringify(draft), before)
})

test('大型模型适应画布后，仍能放大到可阅读的 100% 比例', () => {
  assert.equal(canvasScale(2000,4000,1000,600,null), .138)
  assert.equal(canvasScale(2000,4000,1000,600,1), 1)
  assert.equal(canvasScale(900,500,390,600,null), .38)
})
