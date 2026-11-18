import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../src')
function sources(folder: string): string {
  return readdirSync(folder, { withFileTypes: true }).map(entry => entry.isDirectory()
    ? sources(resolve(folder, entry.name))
    : /\.(tsx?|css)$/.test(entry.name) ? readFileSync(resolve(folder, entry.name), 'utf8') : '').join('\n')
}

test('正式应用源码没有内置示例材料、模拟查询或演示入口', () => {
  const content = sources(root)
  for (const forbidden of ['load-example', 'tracePreview', 'yx186.C_CONS', 'exampleCandidates',
    '采用示例模型', '交互预览', '用一组示例体验完整流程', '示例分析结果']) {
    assert.equal(content.includes(forbidden), false, `正式源码仍含 ${forbidden}`)
  }
})

test('应用先验证服务端会话再挂载业务工作台', () => {
  const app = readFileSync(resolve(root, 'app/SessionGate.tsx'), 'utf8')
  assert.ok(app.includes('auth/session'))
  assert.ok(app.includes('LoginPage'))
  assert.ok(app.includes('session-expired'))
})
