import { useEffect, useState } from 'react'
import MetricCard from '../components/MetricCard'
import RequestTable from '../components/RequestTable'
import StatusBadge from '../components/StatusBadge'
import { AsyncState } from '../components/AsyncState'
import { getWorkbenchSummary, listTraceRequests } from '../services/mockService'
import type { TraceRequest, WorkbenchSummary } from '../domain/types'

export default function WorkbenchPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [summary, setSummary] = useState<WorkbenchSummary>()
  const [requests, setRequests] = useState<TraceRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => {
    setLoading(true); setError('')
    Promise.all([getWorkbenchSummary(), listTraceRequests()]).then(([nextSummary, nextRequests]) => {
      setSummary(nextSummary); setRequests(nextRequests)
    }).catch(e => setError(e instanceof Error ? e.message : '工作台读取失败')).finally(() => setLoading(false))
  }
  useEffect(load, [])
  return <AsyncState loading={loading} error={error} onRetry={load}>
    {summary && <><div className="page-head">
      <div><p className="page-kicker">FIELD TRACE / WORKBENCH</p><h1>我的工作台</h1><p>从真实需求出发，查看字段来源、处理待复核事项，并跟踪当前知识版本。</p></div>
      <div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/knowledge')}>查看知识状态</button><button className="btn primary" type="button" onClick={() => onNavigate('/requests/new')}>新建溯源需求</button></div>
    </div>
    <div className="grid grid-4">
      <MetricCard label="当前发布版本" value={summary.latestVersion.id} hint={`${summary.latestVersion.summary.coverage}% 字段覆盖 · ${summary.latestVersion.createdAt}`} tone="gold" />
      <MetricCard label="我的需求" value={summary.requestCounts.total} hint={`${summary.requestCounts.completed} 条已完成`} />
      <MetricCard label="待处理复核" value={summary.openReviews} hint="需要建模或审核人员接手" tone="amber" />
      <MetricCard label="知识覆盖率" value={`${summary.knowledgeCoverage}%`} hint="首批营销域页面范围" tone="green" />
    </div>
    <div className="grid grid-2 section-gap">
      <section className="panel"><div className="panel-head"><div><h2>需要处理</h2><p>系统把结果风险和协作事项单独列出。</p></div><StatusBadge label="实时工作区" tone="blue" /></div><div className="panel-body">
        <div className="grid">{summary.alerts.map(alert => <button className="notice" key={alert.id} type="button" onClick={() => onNavigate(alert.href)}><StatusBadge label="" tone={alert.tone} /><span><strong>{alert.title}</strong><br />{alert.detail}</span><span className="top-spacer">→</span></button>)}</div>
      </div></section>
      <section className="panel"><div className="panel-head"><div><h2>当前版本</h2><p>查询结果在执行时固定版本，不随草稿变化。</p></div><StatusBadge label="已发布" tone="green" /></div><div className="panel-body"><dl className="detail-kv">
        <dt>版本</dt><dd><code>{summary.latestVersion.id}</code> {summary.latestVersion.label}</dd>
        <dt>范围</dt><dd>{summary.latestVersion.summary.concepts} 个对象 · {summary.latestVersion.summary.attributes} 个属性 · {summary.latestVersion.summary.relations} 条关系</dd>
        <dt>材料快照</dt><dd className="mono">{summary.latestVersion.sourceSnapshot}</dd>
        <dt>最近发布</dt><dd>{summary.latestVersion.createdAt} · {summary.latestVersion.createdBy}</dd>
      </dl></div></section>
    </div>
    <section className="panel section-gap"><div className="panel-head"><div><h2>最近的溯源需求</h2><p>历史执行保留原知识版本；点击需求查看字段级证据。</p></div><button className="btn quiet" type="button" onClick={() => onNavigate('/requests/new')}>新建需求</button></div><div className="panel-body flush"><RequestTable requests={requests} onSelect={id => onNavigate(`/requests/${id}`)} /></div></section>
    </>}
  </AsyncState>
}
