export async function checkHealth(signal: AbortSignal): Promise<boolean> {
  const response = await fetch('/api/healthz', { signal, credentials: 'same-origin' })
  if (!response.ok) return false
  const body: unknown = await response.json()
  return typeof body === 'object' && body !== null && 'status' in body && body.status === 'ok'
}
