import test from 'node:test'
import assert from 'node:assert/strict'
import { initialPreview, previewReducer } from './fixtures/modeling-preview.ts'
import { layoutOntology } from '../src/modules/modeling/ontology-layout.ts'

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
