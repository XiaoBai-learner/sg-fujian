import assert from 'node:assert/strict'
import { test } from 'node:test'
import { initialWorkspace } from '../src/services/workspace.ts'
import { adoptModelPreview, collectModelingInputs, generateModelPreview, readModelingFiles } from '../src/services/modeling.ts'

test('已接入结构、DDL 与有正文的业务文档可一起用于建模，登记文件不能冒充已解析', () => {
  const state = initialWorkspace()
  state.materials = [
    { id: 'doc', kind: '业务说明', name: '说明.md', size: 40, text: '用电客户包括户号和客户名称。' },
    { id: 'ddl', kind: 'DDL', name: '接入.sql', size: 90, text: "CREATE TABLE yx186.NEW_TABLE (ID INT NOT NULL PRIMARY KEY);" },
    { id: 'pdf', kind: '业务说明', name: '扫描件.pdf', size: 200 },
  ]
  const inputs = collectModelingInputs(state)
  assert.deepEqual(inputs.filter(input => input.ready).map(input => input.id), ['source:1', 'material:doc', 'material:ddl'])
  assert.equal(inputs.find(input => input.id === 'material:pdf')?.ready, false)
})

test('接入 DDL 能产生独立于现有示例的本体草稿，保留复合主键和字段类型', () => {
  const state = initialWorkspace()
  state.materials = [{ id: 'new-ddl', kind: 'DDL', name: '新表.sql', size: 200, text: `
    CREATE TABLE other_db.NEW_TABLE (
      A_ID BIGINT NOT NULL COMMENT '业务编号',
      B_ID VARCHAR(30) NOT NULL,
      AMOUNT DECIMAL(12, 2) COMMENT '业务金额',
      PRIMARY KEY (A_ID, B_ID)
    ) COMMENT='新业务对象';` }]
  const preview = generateModelPreview(state, ['material:new-ddl'])
  assert.equal(preview.model.concepts.length, 1)
  assert.equal(preview.model.concepts[0].name, '新业务对象')
  assert.equal(preview.model.attributes.find(a => a.name === '业务金额')?.datatype, 'decimal')
  assert.deepEqual(preview.bindings[0].key_columns, ['A_ID', 'B_ID'])
  const next = adoptModelPreview(state, preview)
  assert.equal(next.editors.model.concepts.length, state.editors.model.concepts.length + 1)
  const binding = next.editors.pipeline.bindings.find(item => item.table_name === 'NEW_TABLE')!
  assert.equal(next.sources.find(source => source.id === binding.data_source_id)?.tables[0].name, 'NEW_TABLE')
  assert.deepEqual(next.active, state.active)
  assert.equal(state.editors.model.concepts.length, 3)
})

test('没有正文的材料和已变化的草稿不能被采用，不会用示例结果冒充生成', () => {
  const state = initialWorkspace()
  state.materials = [{ id: 'pdf', name: '业务.pdf', kind: '业务说明', size: 100 }]
  assert.throws(() => generateModelPreview(state, ['material:pdf']), /正文|解析/)
  assert.throws(() => generateModelPreview(state, []), /选择/)
  const preview = generateModelPreview(state, ['source:1'])
  state.editors.model.concepts[0].description = '用户刚刚修改的定义'
  assert.throws(() => adoptModelPreview(state, preview), /变化/)
})

test('读取上传文本的实际内容，PDF 保留待解析状态，并拒绝超限文件', async () => {
  const materials = await readModelingFiles([
    new File(['用电客户拥有户号'], '业务说明.md'),
    new File(['CREATE TABLE demo.T (ID INT PRIMARY KEY);'], '结构.sql'),
    new File(['%PDF'], '业务.pdf'),
  ])
  assert.equal(materials[0].text, '用电客户拥有户号')
  assert.equal(materials[1].kind, 'DDL')
  assert.equal(materials[2].text, undefined)
  await assert.rejects(() => readModelingFiles([new File(['a'.repeat(1024 * 1024 + 1)], '大文件.txt')]), /1 MB/)
})
