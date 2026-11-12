import StatusBadge from '../components/StatusBadge'

const connections = [
  { name: '营销业务应用', kind: 'Oracle 只读连接', status: '已采集', snapshot: 'snapshot-20261111-01', tables: 28, updated: '2026-11-11 18:20' },
  { name: '用电信息采集', kind: 'Oracle 只读连接', status: '已采集', snapshot: 'snapshot-20261111-01', tables: 19, updated: '2026-11-11 18:20' },
  { name: '数据中台', kind: 'MaxCompute DDL / 血缘导入', status: '部分材料', snapshot: 'snapshot-20261111-01', tables: 41, updated: '2026-11-11 17:58' },
]

export default function ConnectionsPage() {
  return <><div className="page-head"><div><p className="page-kicker">SYSTEM ADMIN / CONNECTIONS</p><h1>系统连接</h1><p>连接凭据和结构快照分开管理；产品查询使用已选快照，不直接读取客户业务数据。</p></div><div className="page-actions"><button className="btn" type="button" onClick={() => alert('原型：这里会打开只读连接配置。')}>新增连接</button><button className="btn primary" type="button" onClick={() => alert('原型：这里会创建结构采集任务。')}>采集结构</button></div></div>
  <div className="notice section-gap"><span><strong>数据边界</strong> · 结构采集只读取 information_schema 或导入 DDL；真实业务行数据需要额外授权，不作为默认证据来源。</span></div>
  <section className="panel section-gap"><div className="panel-head"><div><h2>已注册系统</h2><p>连接状态、快照和库表范围是构建输入的一部分。</p></div><StatusBadge label="3 个系统" tone="blue" /></div><div className="panel-body flush"><div className="table-wrap"><table className="data-table"><thead><tr><th>系统</th><th>类型</th><th>状态</th><th>当前快照</th><th>范围</th><th>最近采集</th></tr></thead><tbody>{connections.map(item => <tr key={item.name}><td><div className="primary-cell">{item.name}</div><div className="muted-cell">凭据：已托管，不在页面显示</div></td><td>{item.kind}</td><td><StatusBadge label={item.status} tone={item.status === '已采集' ? 'green' : 'amber'} /></td><td><code>{item.snapshot}</code></td><td>{item.tables} 张表</td><td>{item.updated}</td></tr>)}</tbody></table></div></div></section></>
}
