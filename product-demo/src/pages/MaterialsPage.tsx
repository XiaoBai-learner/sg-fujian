import { useEffect, useState } from 'react'
import { AsyncState } from '../components/AsyncState'
import StatusBadge from '../components/StatusBadge'
import type { Material } from '../domain/types'
import { listMaterials } from '../services/mockService'

const categoryLabels: Record<Material['category'], string> = { ddl: '数据库 DDL', lineage: 'DataWorks 血缘', task_sql: '任务 SQL', business_doc: '业务说明' }
const statusLabels: Record<Material['status'], { label: string; tone: 'green' | 'amber' | 'red' }> = {
  ready: { label: '已参与构建', tone: 'green' }, parsing: { label: '解析中', tone: 'amber' }, partial: { label: '部分解析', tone: 'amber' }, failed: { label: '解析失败', tone: 'red' },
}

export default function MaterialsPage() {
  const [items, setItems] = useState<Material[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Material>()
  const load = () => { setLoading(true); listMaterials().then(setItems).catch(e => setError(e instanceof Error ? e.message : '材料读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [])
  return <AsyncState loading={loading} error={error} onRetry={load}><><div className="page-head"><div><p className="page-kicker">KNOWLEDGE WORKSPACE / MATERIALS</p><h1>资料与结构</h1><p>每份材料都有来源、修订、解析结果和覆盖范围。解析不完整时会留下可处理的问题项。</p></div><div className="page-actions"><button className="btn" type="button" onClick={() => alert('原型：这里会打开材料导入任务。')}>导入材料</button><button className="btn primary" type="button" onClick={() => alert('原型：这里会创建结构采集任务。')}>采集最新结构</button></div></div>
    <div className="notice section-gap"><span><strong>当前材料快照 snapshot-20261111-01</strong> · 现场结构和任务材料是候选知识的输入，上传附件不会直接改写线上版本。</span></div>
    <section className="panel section-gap"><div className="panel-head"><div><h2>材料清单</h2><p>点击材料查看来源范围、解析问题和引用片段。</p></div><StatusBadge label={`${items.length} 份材料`} tone="blue" /></div><div className="panel-body flush"><div className="table-wrap"><table className="data-table"><thead><tr><th>材料</th><th>类别</th><th>状态</th><th>覆盖范围</th><th>更新时间</th><th /></tr></thead><tbody>{items.map(item => { const status = statusLabels[item.status]; return <tr key={item.id}><td><div className="primary-cell">{item.name}</div><div className="muted-cell">{item.source}</div></td><td>{categoryLabels[item.category]}</td><td><StatusBadge label={status.label} tone={status.tone} /><div className="muted-cell">{item.issueCount ? `${item.issueCount} 个问题` : '无问题'}</div></td><td><div className="progress-line"><div className="progress-bar"><span style={{ width: `${item.coverage}%` }} /></div><span>{item.coverage}%</span></div><div className="muted-cell">{item.scope}</div></td><td>{item.updatedAt}</td><td><button className="btn quiet" type="button" onClick={() => setSelected(item)}>查看详情</button></td></tr> })}</tbody></table></div></div></section>
    {selected && <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="material-title"><header className="modal-head"><div><h2 id="material-title">{selected.name}</h2><p>{selected.source} · {selected.updatedAt}</p></div><button className="close" type="button" aria-label="关闭" onClick={() => setSelected(undefined)}>×</button></header><div className="modal-body"><dl className="detail-kv"><dt>解析状态</dt><dd><StatusBadge label={statusLabels[selected.status].label} tone={statusLabels[selected.status].tone} /></dd><dt>覆盖范围</dt><dd>{selected.scope} · {selected.coverage}%</dd><dt>解析摘要</dt><dd>{selected.excerpt}</dd><dt>问题处理</dt><dd>{selected.issueCount ? `有 ${selected.issueCount} 个问题等待维护人员处理。` : '当前没有待处理问题。'}</dd></dl><div className="notice section-gap"><span><strong>来源片段预览</strong><br />{selected.excerpt}。这里会展示可定位到的原文行号和解析器信息。</span></div></div><footer className="modal-foot"><button className="btn" type="button" onClick={() => setSelected(undefined)}>关闭</button></footer></section></div>}
  </></AsyncState>
}
