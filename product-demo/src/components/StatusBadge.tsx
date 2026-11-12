import type { ReactNode } from 'react'
import type { Tone } from '../domain/types'

const toneClass: Record<Tone, string> = {
  green: 'green', amber: 'amber', red: 'red', blue: 'blue', gold: 'gold', neutral: 'neutral', purple: 'purple',
}

export default function StatusBadge({ label, tone = 'neutral', dot = true }: { label: ReactNode; tone?: Tone; dot?: boolean }) {
  return <span className={`status ${toneClass[tone] || 'neutral'}`}>{dot && <i className="status-dot" aria-hidden="true" />}{label}</span>
}
