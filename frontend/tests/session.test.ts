import test from 'node:test'
import assert from 'node:assert/strict'
import { apiFetch, setSession } from '../src/shared/api/session.ts'

test('请求携带内存中的 CSRF，401 清除会话并通知登录门禁', async () => {
  const originalFetch = globalThis.fetch
  const originalWindow = globalThis.window
  const events = new EventTarget()
  let expired = 0
  events.addEventListener('session-expired', () => expired++)
  Object.assign(globalThis, { window: events })
  try {
    setSession({ user: { id: 'u', username: 'user', display_name: '成员', active: true, created_at: '' }, csrf_token: 'token' })
    globalThis.fetch = async (_, options) => {
      assert.equal(options?.credentials, 'same-origin')
      assert.equal(new Headers(options?.headers).get('X-CSRF-Token'), 'token')
      return new Response('{}', { status: 401 })
    }
    await apiFetch('/api/v1/modeling/trace', { method: 'POST' })
    assert.equal(expired, 1)
    globalThis.fetch = async (_, options) => {
      assert.equal(new Headers(options?.headers).has('X-CSRF-Token'), false)
      return new Response('{}')
    }
    await apiFetch('/api/v1/materials', { method: 'POST' })
  } finally {
    globalThis.fetch = originalFetch
    Object.assign(globalThis, { window: originalWindow })
    setSession(null)
  }
})
