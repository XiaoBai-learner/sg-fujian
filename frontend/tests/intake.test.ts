import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (path: string) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('正式工作台不再硬编码领域名称或重复全局导航', () => {
  const app = read('app/App.tsx')
  assert.equal(app.includes('营销域'), false)
  assert.equal(app.includes('product-navigation'), false)
  assert.ok(app.includes('数据库连接') && app.includes('文档材料'))
  const catalog = read('modules/modeling/ModelCatalog.tsx')
  assert.equal(catalog.includes('model-groups'), false)
  assert.equal(catalog.includes('全部模型'), false)
})

test('文件上传集中在数据接入，模型页只选择已有材料和补充流程说明', () => {
  const model = read('modules/modeling/index.tsx')
  assert.equal(model.includes('MaterialInput'), false)
  assert.ok(model.includes('MaterialPicker'))
  assert.ok(model.includes('业务流程说明'))
  assert.equal(read('modules/sources/MaterialsPage.tsx').includes('新建文档'), true)
})

test('导入文档读取原始正文、识别类型，拒绝损坏或超限文件', async () => {
  const { readMaterial, documentSummary } = await import('../src/modules/sources/document.ts')
  const ddl = await readMaterial(new File(["CREATE TABLE db.CUSTOMER (ID BIGINT);"], 'customer.sql'))
  assert.equal(ddl.kind, 'DDL')
  assert.ok(ddl.body.includes('db.CUSTOMER'))
  const sql = await readMaterial(new File(['SELECT ID FROM db.CUSTOMER;'], 'queries.sql'))
  assert.equal(sql.kind, '热点 SQL')
  const document = await readMaterial(new File(['# 业务流程\n先建档再安装设备'], '流程.md'))
  assert.equal(document.kind, '业务说明')
  assert.equal(documentSummary(document.body), '业务流程')
  await assert.rejects(readMaterial(new File([''], 'empty.txt')), /没有可用/)
  await assert.rejects(readMaterial(new File([new Uint8Array([255])], 'broken.txt')), /UTF-8/)
  await assert.rejects(readMaterial(new File(['x'.repeat(2_000_001)], 'large.txt')), /2 MB/)
  await assert.rejects(readMaterial(new File(['body'], 'unsupported.pdf')), /SQL、TXT/)
})
