import type { FieldResult } from '../domain/types'
import StatusBadge from './StatusBadge'

const kindLabel = { direct: '直接映射', calculated: '计算字段', rule: '分类规则' }

export default function EvidencePanel({ field }: { field?: FieldResult }) {
  if (!field) return <div className="panel sticky-panel"><div className="empty-state"><strong>选择一个字段</strong><p>点击左侧字段查看来源证据。</p></div></div>
  return <aside className="panel sticky-panel"><div className="panel-head"><div><p className="page-kicker">FIELD EVIDENCE</p><h2>{field.label}</h2><p>{kindLabel[field.resultKind]} · 结果状态独立于匹配分。</p></div><StatusBadge label={field.evidenceStatus === 'verified' ? '已核验' : field.evidenceStatus === 'conflict' ? '存在冲突' : '需要补充'} tone={field.evidenceStatus === 'verified' ? 'green' : field.evidenceStatus === 'conflict' ? 'red' : 'amber'} /></div><div className="panel-body">
    {field.actualSource ? <div className="notice ok"><span><strong>页面实际来源</strong><br /><code>{field.actualSource.column}</code><br />{field.actualSource.tableComment} · {field.actualSource.fieldComment}</span></div> : <div className="notice warn"><span><strong>当前没有确定性来源</strong><br />系统会保留候选和缺口，不把候选列显示为正式答案。</span></div>}
    {field.note && <div className="notice section-gap"><span>{field.note}</span></div>}
    {field.calculation && <div className="section-gap"><h3>计算口径</h3><dl className="detail-kv">
      <dt>表达式</dt><dd><code>{field.calculation.expression}</code></dd>
      <dt>粒度</dt><dd>{field.calculation.grain}</dd>
      <dt>过滤</dt><dd>{field.calculation.filters.join('；')}</dd>
      <dt>关联</dt><dd>{field.calculation.joins.join('；')}</dd>
    </dl></div>}
    <div className="section-gap"><h3>本体与映射证据</h3><div className="evidence-list">{field.evidence.map(item => <div className="evidence-item" key={item.id}><header><b>{item.label}</b><StatusBadge dot={false} label={item.status === 'verified' ? '已核验' : item.status === 'conflict' ? '冲突' : '部分支持'} tone={item.status === 'verified' ? 'green' : item.status === 'conflict' ? 'red' : 'amber'} /></header><p>{item.summary}</p><p className="muted-cell">{item.sourceName}{item.location ? ` · ${item.location}` : ''}</p></div>)}</div></div>
    {field.lineage.length > 0 && <div className="section-gap"><h3>逐跳血缘</h3><div className="lineage">{field.lineage.map((step, index) => <div className="lineage-row" key={`${step.from}-${step.to}-${index}`}><code>{step.from}</code><span>→</span><code>{step.to}</code><small className="muted-cell">{step.action}{step.expression ? ` · ${step.expression}` : ''}</small></div>)}</div></div>}
    {field.equivalents.length > 0 && <div className="section-gap"><h3>相关等价字段</h3>{field.equivalents.map(item => <div className="evidence-item" key={item.id}><code>{item.column}</code><p>{item.tableComment} · {item.fieldComment}</p></div>)}</div>}
    {field.candidates.length > 0 && <div className="section-gap"><h3>待确认候选</h3>{field.candidates.map(item => <div className="evidence-item" key={item.id}><code>{item.column}</code><p>{item.tableComment} · {item.fieldComment}</p></div>)}</div>}
  </div></aside>
}
