import test from 'node:test'
import assert from 'node:assert/strict'
import { initialWorkspace, workspaceReducer, type WorkspaceState } from '../src/modules/modeling/state.ts'

function state(): WorkspaceState {
  const evidence = [{materialId: 'user-upload', label: 'DDL', quote: "NAME VARCHAR(60) COMMENT '名称'"}]
  const cls = {id: 'entity', name: '对象', aliases: [], description: '', parentId: null, evidence}
  const property = {id: 'name', name: '名称', aliases: [], description: '', concept: '对象', conceptId: cls.id,
    datatype: 'string' as const, unit: '', kind: 'direct' as const, sources: ['userdb.ENTITY.NAME'], evidence}
  return {...initialWorkspace(), draft: {revision: 1, classes: [cls], relations: [], items: [property]},
    active: {snapshotId: 'adopted', version: 1, classes: [cls], relations: [], items: [property]}}
}

test('正式草稿编辑保留物理证据、采用模型和稳定引用', () => {
  const current = state()
  const next = workspaceReducer(current, {type: 'edit-property', value: {
    ...current.draft!.items[0], name: '新名称', sources: ['invented.table.column'], evidence: [],
  }})
  assert.equal(next.draft!.revision, 2)
  assert.deepEqual(next.draft!.items[0].sources, ['userdb.ENTITY.NAME'])
  assert.deepEqual(next.draft!.items[0].evidence, current.draft!.items[0].evidence)
  assert.equal(next.active!.items[0].name, '名称')
})

test('正式状态不能在本地校验或采用模型冒充服务端结果', () => {
  for (const type of ['validate', 'adopt'] as const) {
    const current = state()
    const next = workspaceReducer(current, {type})
    assert.ok(next.error.includes('服务端'))
    assert.equal(next.active, current.active)
    assert.equal(next.validation, null)
  }
})
