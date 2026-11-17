import test from 'node:test'
import assert from 'node:assert/strict'
import { initialPreview, previewReducer, tracePreview } from '../src/modules/modeling/preview.ts'

const prepared = () => previewReducer(previewReducer(initialPreview(), { type: 'load-example' }), { type: 'generate' })

test('custom materials cannot receive the example ontology', () => {
  let state = previewReducer(initialPreview(), { type: 'load-example' })
  state = previewReducer(state, { type: 'add-materials', materials: [
    { id: 'custom', name: '其他系统.sql', kind: 'DDL', origin: 'upload', body: 'CREATE TABLE other (id INT);', size: 35 },
  ] })
  state = previewReducer(state, { type: 'generate' })
  assert.equal(state.draft, null)
  assert.match(state.error, /识别服务/)
})

test('adoption requires fresh validation and preserves the previous snapshot after draft edits', () => {
  let state = prepared()
  assert.equal(previewReducer(state, { type: 'adopt' }).active, null)
  state = previewReducer(state, { type: 'validate' })
  state = previewReducer(state, { type: 'adopt' })
  assert.equal(state.active?.version, 1)
  assert.equal(tracePreview(state.active, '户号').sources[0], 'yx186.C_CONS.CONS_NO')
  state = previewReducer(state, { type: 'exclude', id: 'cons-no', excluded: true })
  assert.equal(state.validation, null)
  assert.equal(previewReducer(state, { type: 'adopt' }).active?.version, 1)
  assert.equal(tracePreview(state.active, '户号').status, 'located')
})

test('input changes invalidate the draft without changing the adopted version', () => {
  let state = previewReducer(previewReducer(prepared(), { type: 'validate' }), { type: 'adopt' })
  state = previewReducer(state, { type: 'toggle-material', id: 'example-ddl' })
  assert.equal(state.draft, null)
  assert.equal(state.validation, null)
  assert.equal(state.active?.version, 1)
})

test('ambiguous and unknown fields are withheld from adopted lookup', () => {
  const state = previewReducer(previewReducer(prepared(), { type: 'validate' }), { type: 'adopt' })
  assert.equal(state.active?.items.length, 4)
  assert.equal(tracePreview(state.active, '联系电话').status, 'not_found')
  assert.equal(tracePreview(state.active, '发电量').status, 'not_found')
  assert.equal(tracePreview(null, '户号').status, 'no_model')
  assert.equal(tracePreview(state.active, '欠费金额').kind, 'calculated')
})

test('validation reports source-set mistakes rather than marking every case as passed', () => {
  let state = prepared()
  state = { ...state, draft: { ...state.draft!, items: state.draft!.items.map(item =>
    item.id === 'cons-no' ? { ...item, sources: ['yx186.C_CONS.CONS_NAME'] } : item) } }
  state = previewReducer(state, { type: 'validate' })
  assert.equal(state.validation?.cases.find(item => item.field === '户号')?.passed, false)
  assert.equal(previewReducer(state, { type: 'adopt' }).active, null)
})

test('excluded fields are explicitly skipped, allowing adoption of the remaining validated scope', () => {
  let state = previewReducer(prepared(), { type: 'exclude', id: 'cons-no', excluded: true })
  state = previewReducer(state, { type: 'validate' })
  const excluded = state.validation?.cases.find(item => item.field === '户号')
  assert.equal(excluded?.skipped, true)
  assert.equal(excluded?.passed, false)
  state = previewReducer(state, { type: 'adopt' })
  assert.equal(state.active?.items.length, 3)
  assert.equal(tracePreview(state.active, '户号').status, 'not_found')
  assert.equal(tracePreview(state.active, '客户名称').status, 'located')
})

test('all candidate evidence quotes are locatable in the selected example materials', () => {
  const state = prepared()
  for (const candidate of state.draft!.items) {
    assert.ok(candidate.evidence.length > 0)
    for (const evidence of candidate.evidence) {
      const material = state.materials.find(material => material.id === evidence.materialId)
      assert.ok(material?.body.includes(evidence.quote), `${candidate.name}: ${evidence.label}`)
    }
  }
})
