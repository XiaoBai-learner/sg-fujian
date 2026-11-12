import type { VersionDiff } from '../domain/types'
import StatusBadge from './StatusBadge'

const labels = { added: '新增', changed: '变更', blocked: '阻断', removed: '移除' }
const tones = { added: 'green', changed: 'amber', blocked: 'red', removed: 'blue' } as const

export default function VersionDiffView({ diff }: { diff: VersionDiff }) {
  return <div className="grid"><div className="notice"><span><strong>{diff.current.id}</strong> → <strong>{diff.candidate.id}</strong><br />对比范围：{diff.changes.length} 项变化，影响 {diff.candidate.affectedFields.length} 个字段。</span><StatusBadge label={diff.candidate.status === 'review' ? '待审核' : diff.candidate.status} tone={diff.candidate.status === 'review' ? 'amber' : 'green'} /></div><div className="diff-list">{diff.changes.map(change => <div className="diff-item" key={`${change.type}-${change.label}`}><StatusBadge label={labels[change.type]} tone={tones[change.type]} /><div><b>{change.label}</b><p>{change.detail}</p><small className="muted-cell">影响：{change.affected.join('、')}</small></div></div>)}</div></div>
}
