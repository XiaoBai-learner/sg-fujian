import type { TraceRequest } from '../domain/types'
import StatusBadge from './StatusBadge'

const statusMeta: Record<TraceRequest['status'], { label: string; tone: 'green' | 'amber' | 'blue' }> = {
  draft: { label: '草稿', tone: 'blue' },
  running: { label: '处理中', tone: 'amber' },
  completed: { label: '已完成', tone: 'green' },
  needs_review: { label: '待复核', tone: 'amber' },
}

export default function RequestTable({ requests, onSelect }: { requests: TraceRequest[]; onSelect: (id: string) => void }) {
  return <div className="table-wrap"><table className="data-table">
    <thead><tr><th>需求</th><th>页面上下文</th><th>字段数</th><th>状态</th><th>提交时间</th><th /></tr></thead>
    <tbody>{requests.map(request => {
      const meta = statusMeta[request.status]
      return <tr key={request.id}>
        <td><div className="primary-cell">{request.title}</div><div className="muted-cell mono">{request.id}</div></td>
        <td><div className="primary-cell">{request.page}</div><div className="muted-cell">{request.system}</div></td>
        <td>{request.fields.length} 个字段</td>
        <td><StatusBadge label={meta.label} tone={meta.tone} /></td>
        <td><button className="btn quiet" type="button" onClick={() => onSelect(request.id)}>查看需求</button></td>
      </tr>
    })}</tbody>
  </table></div>
}
