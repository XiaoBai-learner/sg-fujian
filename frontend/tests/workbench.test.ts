import test from 'node:test'
import assert from 'node:assert/strict'
import { workspaceReducer, initialWorkspace } from '../src/modules/modeling/state.ts'
import { groupModels, modelPath, modelIdFromPath } from '../src/modules/modeling/catalog.ts'

test('模型目录分组及独立地址不混用其他模型', () => {
  const models = [{id:'a',name:'客户',group:'营销'}, {id:'b',name:'计量',group:'采集'}, {id:'c',name:'账单',group:'营销'}]
  assert.deepEqual(groupModels(models).map(([group, entries]) => [group, entries.length]), [['营销',2],['采集',1]])
  assert.equal(modelIdFromPath(modelPath('model-123')), 'model-123')
  assert.equal(modelIdFromPath('/modeling'), null)
  assert.equal(modelIdFromPath('/agent'), null)
})

test('增减建模材料不会丢失服务端草稿和校验记录', () => {
  const draft = {revision:7,classes:[],relations:[],items:[]}
  const state = {...initialWorkspace(), draft, selected:['m'], live:{runId:'r',stats:{},diagnostics:[],method:'real',check:null}}
  const changed = workspaceReducer(state, {type:'toggle-material',id:'m'})
  assert.equal(changed.draft, draft)
  assert.equal(changed.live?.runId, 'r')
  const added = workspaceReducer(state, {type:'add-materials',materials:[{id:'n',name:'new.sql',kind:'DDL',origin:'upload',body:'DDL',size:3}]})
  assert.equal(added.draft, draft)
  assert.equal(added.live?.runId, 'r')
})
