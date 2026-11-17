import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const css = readFileSync(new URL('../src/app/styles.css', import.meta.url), 'utf8')

test('字段溯源工作区使用完整主区宽度并让输入区随视口扩展', () => {
  assert.match(css, /\.agent-body\s*\{[^}]*width:\s*auto/)
  assert.match(css, /\.agent-body\s*\{[^}]*max-width:\s*none/)
  assert.match(css, /\.agent-body\s*\{[^}]*flex-direction:\s*column/)
  assert.match(css, /\.agent-stage\s*\{[^}]*width:\s*min\(1100px,\s*100%\)/)
})
