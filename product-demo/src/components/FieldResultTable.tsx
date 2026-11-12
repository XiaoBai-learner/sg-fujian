import type { FieldResult } from '../domain/types'
import StatusBadge from './StatusBadge'

const statusMeta: Record<FieldResult['locationStatus'], { label: string; tone: 'green' | 'amber' | 'red' | 'blue' }> = {
  located: { label: '已定位', tone: 'green' },
  needs_clarification: { label: '需澄清', tone: 'amber' },
  insufficient_evidence: { label: '证据不足', tone: 'red' },
  out_of_scope: { label: '未覆盖', tone: 'blue' },
}
const kindLabel: Record<FieldResult['resultKind'], string> = { direct: '直接映射', calculated: '计算字段', rule: '分类规则' }

export default function FieldResultTable({ results, selectedId, onSelect }: { results: FieldResult[]; selectedId?: string; onSelect: (result: FieldResult) => void }) {
  return <div className="table-wrap"><table className="data-table">
    <thead><tr><th>页面字段</th><th>结论</th><th>实际来源 / 口径</th><th>证据</th><th>置信度</th></tr></thead>
    <tbody>{results.map(result => {
      const meta = statusMeta[result.locationStatus]
      const confidence = result.confidence >= .8 ? 'high' : result.confidence >= .5 ? 'medium' : 'low'
      return <tr key={result.id} className={`field-row${selectedId === result.id ? ' selected' : ''}`} onClick={() => onSelect(result)}>
        <td><span className="field-label">{result.label}</span><span className="field-kind">{kindLabel[result.resultKind]}</span></td>
        <td><StatusBadge label={meta.label} tone={meta.tone} /></td>
        <td>{result.actualSource ? <><code>{result.actualSource.column}</code><div className="muted-cell">{result.actualSource.fieldComment || result.actualSource.tableComment}</div></> : result.calculation ? <><code>{result.calculation.expression}</code><div className="muted-cell">等待完整页面口径</div></> : <span className="muted-cell">没有已确认来源</span>}</td>
        <td><StatusBadge label={result.evidenceStatus === 'verified' ? '已核验' : result.evidenceStatus === 'conflict' ? '存在冲突' : result.evidenceStatus === 'partial' ? '部分支持' : '已过期'} tone={result.evidenceStatus === 'verified' ? 'green' : result.evidenceStatus === 'conflict' ? 'red' : 'amber'} /></td>
        <td><span className={`confidence ${confidence}`}>{Math.round(result.confidence * 100)}%</span></td>
      </tr>
    })}</tbody>
  </table></div>
}
