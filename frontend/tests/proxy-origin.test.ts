import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer as httpServer, type Server } from 'node:http'
import { createServer as viteServer } from 'vite'
import config from '../vite.config.ts'
import { fileURLToPath } from 'node:url'

async function listen(server: Server) {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  assert.ok(address && typeof address !== 'string')
  return `http://127.0.0.1:${address.port}`
}

async function close(server: Server) {
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
}

test('实际 Vite 代理保留浏览器 Host 和 Origin，合法来源一致，跨站来源不被改写', async () => {
  const backend = httpServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    response.end(JSON.stringify({host: request.headers.host, origin: request.headers.origin}))
  })
  const target = await listen(backend)
  const configured = config.server!.proxy!['/api']
  const proxy = typeof configured === 'string' ? target : {...configured, target}
  const vite = await viteServer({...config, root: fileURLToPath(new URL('..', import.meta.url)), configFile: false, server: {
    ...config.server, middlewareMode: true, hmr: false, proxy: {'/api': proxy},
  }})
  const frontend = httpServer(vite.middlewares)
  try {
    const origin = await listen(frontend)
    const response = await fetch(`${origin}/api/auth-origin-check`, {method: 'POST', headers: {Origin: origin}})
    assert.equal(response.status, 200)
    const headers = await response.json()
    assert.equal(headers.host, new URL(origin).host)
    assert.equal(headers.origin, origin)

    const crossSite = await fetch(`${origin}/api/auth-origin-check`, {
      method: 'POST', headers: {Origin: 'https://untrusted.example'},
    })
    const forwarded = await crossSite.json()
    assert.equal(forwarded.host, new URL(origin).host)
    assert.equal(forwarded.origin, 'https://untrusted.example')
  } finally {
    await close(frontend)
    await vite.close()
    await close(backend)
  }
})
