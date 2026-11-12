import type { ReactNode } from 'react'

export function LoadingState({ label = '正在读取…' }: { label?: string }) {
  return <div className="loading-state" role="status">{label}</div>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="error-state" role="alert"><strong>读取失败</strong><p>{message}</p>{onRetry && <button className="btn" type="button" onClick={onRetry}>重新读取</button>}</div>
}

export function AsyncState({ loading, error, onRetry, children }: { loading: boolean; error: string; onRetry?: () => void; children: ReactNode }) {
  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={onRetry} />
  return <>{children}</>
}
