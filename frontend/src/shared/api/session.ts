export type Account = { id: string; username: string; display_name: string; active: boolean; created_at: string }
export type LoginSession = { user: Account; csrf_token: string }
let csrfToken = ''
export function setSession(session: LoginSession | null) { csrfToken = session?.csrf_token ?? '' }

export async function apiFetch(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  headers.set('X-Requested-With', 'SGTrace')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(options.method ?? 'GET') && csrfToken) headers.set('X-CSRF-Token', csrfToken)
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' })
  if (response.status === 401 && !path.endsWith('/auth/login') && !path.endsWith('/auth/setup')) {
    setSession(null)
    window.dispatchEvent(new Event('session-expired'))
  }
  return response
}

export async function api<T>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const response = await apiFetch(`/api/v1/${path}`, body === undefined ? {} : {
    method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  const value = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new Error(value?.detail?.message || '请求失败，请稍后重试')
  return value as T
}
