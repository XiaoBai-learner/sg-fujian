import type { ReactNode } from 'react'
import type { Tone } from '../domain/types'

export default function MetricCard({ label, value, hint, tone = 'neutral' }: { label: string; value: ReactNode; hint?: string; tone?: Tone }) {
  return <article className={`panel metric-card${tone === 'gold' ? ' accent' : ''}`}>
    <span>{label}</span>
    <strong>{value}</strong>
    {hint && <small>{hint}</small>}
  </article>
}
