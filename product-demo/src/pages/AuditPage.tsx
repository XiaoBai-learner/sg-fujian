import { useEffect, useState } from 'react'
import StatusBadge from '../components/StatusBadge'
import { listAuditEvents } from '../services/mockService'
import type { AuditEvent } from '../domain/types'

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  useEffect(() => { listAuditEvents().then(setEvents) }, [])
  return <><div className="page-head"><div><p className="page-kicker">SYSTEM ADMIN / AUDIT</p><h1>审计记录</h1><p>记录连接、材料、草稿、验证、审核、发布和用户反馈，不记录 OCR 正文和连接密码。</p></div><div className="page-actions"><StatusBadge label="只读视图" tone="blue" /></div></div>
  <section className="panel section-gap"><div className="panel-head"><div><h2>最近事件</h2><p>按时间倒序显示，物理对象和知识版本可追溯。</p></div><span className="version-pill">{events.length} 条</span></div><div className="panel-body flush"><div className="table-wrap"><table className="data-table"><thead><tr><th>时间</th><th>动作</th><th>操作者</th><th>对象</th><th>版本</th><th>说明</th></tr></thead><tbody>{events.map(event => <tr key={event.id}><td className="mono">{event.at}</td><td><StatusBadge label={event.action} tone={event.action.includes('反馈') ? 'amber' : event.action.includes('发布') ? 'green' : 'blue'} /></td><td>{event.actor}</td><td><code>{event.object}</code></td><td>{event.version ? <code>{event.version}</code> : '—'}</td><td>{event.detail}</td></tr>)}</tbody></table></div></div></section></>
}
