import { useEffect, useState } from 'react'
import MetricCard from '../components/MetricCard'
import ReviewQueue from '../components/ReviewQueue'
import StatusBadge from '../components/StatusBadge'
import KnowledgeTabs from '../components/KnowledgeTabs'
import { AsyncState } from '../components/AsyncState'
import { getKnowledgeOverview } from '../services/mockService'
import type { KnowledgeOverview } from '../domain/types'

export default function KnowledgeOverviewPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [overview, setOverview] = useState<KnowledgeOverview>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => { setLoading(true); getKnowledgeOverview().then(setOverview).catch(e => setError(e instanceof Error ? e.message : '知识工作台读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [])
  return <AsyncState loading={loading} error={error} onRetry={load}>{overview && <><div className="page-head"><div><p className="page-kicker">KNOWLEDGE WORKSPACE / OVERVIEW</p><h1>知识工作台</h1><p>管理现场资料、语义模型和可发布知识版本。草稿变化不会影响线上查询。</p></div><div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/knowledge/materials')}>查看材料</button><button className="btn primary" type="button" onClick={() => onNavigate('/knowledge/versions')}>查看版本</button></div></div>
    <KnowledgeTabs active="overview" onChange={id => onNavigate(id === 'overview' ? '/knowledge' : `/knowledge/${id === 'versions' ? 'versions' : id}`)} />
    <div className="grid grid-4 section-gap"><MetricCard label="线上知识版本" value={overview.latestVersion.id} hint={`${overview.latestVersion.summary.coverage}% 范围覆盖`} tone="gold" /><MetricCard label="草稿修订" value={`R${overview.draft.revision}`} hint={`${overview.draft.pendingChanges.length} 项待处理变化`} tone="amber" /><MetricCard label="材料健康" value={`${overview.materialHealth.ready}/${overview.materialHealth.total}`} hint={`${overview.materialHealth.issues} 项有解析问题`} tone="green" /><MetricCard label="待审核事项" value={overview.openReviews.length} hint="反馈与候选版本" tone="red" /></div>
    <div className="grid grid-2 section-gap"><section className="panel"><div className="panel-head"><div><h2>待处理队列</h2><p>反馈、知识修改和版本审核共享同一条责任链。</p></div><StatusBadge label={`${overview.openReviews.length} 项`} tone="amber" /></div><div className="panel-body"><ReviewQueue tasks={overview.openReviews} onSelect={task => onNavigate(task.type === 'release' ? '/knowledge/versions' : '/knowledge/model')} /></div></section><section className="panel"><div className="panel-head"><div><h2>知识健康</h2><p>阻断项和提醒按影响范围排列。</p></div><StatusBadge label={overview.conflicts.length ? '有冲突' : '正常'} tone={overview.conflicts.length ? 'red' : 'green'} /></div><div className="panel-body grid">{overview.conflicts.map(conflict => <div className="notice danger" key={conflict.id}><span><strong>{conflict.label}</strong><br />{conflict.detail}<br /><small className="muted-cell">影响：{conflict.affected.join('、')}</small></span></div>)}{!overview.conflicts.length && <div className="notice ok"><span>当前没有需要阻断发布的语义冲突。</span></div>}</div></section></div>
    <section className="panel section-gap"><div className="panel-head"><div><h2>当前草稿修订</h2><p>{overview.draft.title} · {overview.draft.updatedAt} · {overview.draft.updatedBy}</p></div><button className="btn" type="button" onClick={() => onNavigate('/knowledge/model')}>打开语义模型</button></div><div className="panel-body"><div className="grid grid-4"><MetricCard label="对象" value={overview.draft.concepts} /><MetricCard label="属性" value={overview.draft.attributes} /><MetricCard label="关系" value={overview.draft.relations} /><MetricCard label="规则" value={overview.draft.rules} /></div></div></section>
  </>}</AsyncState>
}
