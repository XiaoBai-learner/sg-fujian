import assert from 'node:assert/strict'
import { test } from 'node:test'
import { initialWorkspace, activateModel, checkModel, traceFields } from '../src/services/workspace.ts'

test('修改草稿不改变智能体，应用后才采用新的属性叫法', () => {
  const state = initialWorkspace()
  const consumerNo = state.editors.model.attributes.find(a => a.id === 'Consumer_consNo')!
  consumerNo.aliases.push('业务专用编号')
  state.revision++
  assert.equal(traceFields(state, ['业务专用编号'])[0].status, 'not_found')
  const next = activateModel(state)
  assert.equal(traceFields(next, ['业务专用编号'])[0].sources[0].column, 'yx186.C_CONS.CONS_NO')
  consumerNo.aliases.push('不应泄漏的修改')
  assert.equal(traceFields(next, ['不应泄漏的修改'])[0].status, 'not_found')
})

test('缺少实体键时不能应用模型，保留上次可用快照', () => {
  const state = initialWorkspace()
  state.editors.pipeline.bindings[0].key_columns = []
  assert.ok(checkModel(state.editors).some(issue => issue.includes('实体键')))
  assert.throws(() => activateModel(state), /实体键/)
  assert.equal(traceFields(state, ['户号'])[0].status, 'located')
})

test('未知字段拒答，存在业务计算口径时保留多个源输入和条件', () => {
  const state = initialWorkspace()
  const results = traceFields(state, ['不存在的字段', '欠费金额'])
  assert.equal(results[0].status, 'not_found')
  assert.equal(results[0].sources.length, 0)
  assert.equal(results[1].kind, 'calculated')
  assert.equal(results[1].sources.length, 2)
  assert.ok(results[1].calculation?.filters.includes("SETTLE_FLAG = '0'"))
})
