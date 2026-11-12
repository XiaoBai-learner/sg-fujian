import { useEffect, useMemo, useState } from 'react'
import { AsyncState } from '../components/AsyncState'
import EvidencePanel from '../components/EvidencePanel'
import FieldResultTable from '../components/FieldResultTable'
import FeedbackDialog from '../components/FeedbackDialog'
import StatusBadge from '../components/StatusBadge'
import { getTraceRequest } from '../services/mockService'
import type { FieldResult, TraceRequest, TraceRun } from '../domain/types'

export default function RequestDetailPage({ requestId, onNavigate }: { requestId: string; onNavigate: (path: string) => void }) {
  const [data, setData] = useState<{ request: TraceRequest; run: TraceRun }>()
  const [selected, setSelected] = useState<FieldResult>()
  const [feedback, setFeedback] = useState<FieldResult>()
  const [toast, setToast] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => { setLoading(true); setError(''); getTraceRequest(requestId).then(next => { setData(next); setSelected(next.run.fieldResults[0]) }).catch(e => setError(e instanceof Error ? e.message : '需求读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [requestId])
  const counts = useMemo(() => {
    const results = data?.run.fieldResults || []
    return { located: results.filter(item => item.locationStatus === 'located').length, clarify: results.filter(item => item.locationStatus === 'needs_clarification').length, gap: results.filter(item => item.locationStatus === 'out_of_scope' || item.locationStatus === 'insufficient_evidence').length }
  }, [data])
  return <AsyncState loading={loading} error={error} onRetry={load}>{data && <><div className="page-head">
    <div><p className="page-kicker">FIELD TRACE / REQUEST DETAIL</p><h1>{data.request.title}</h1><p>{data.request.description}</p></div>
    <div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/workbench')}>返回工作台</button><button className="btn" type="button" onClick={() => setToast('已生成 CSV / HTML 报告任务，稍后可下载。')}>导出结果</button><button className="btn primary" type="button" onClick={() => setToast('已提交整条需求复核，维护人员会在站内处理。')}>提交复核</button></div>
  </div>
  <div className="notice section-gap"><span><strong>本次执行固定版本 {data.run.knowledgeVersionId}</strong> · {data.run.note} 页面发布新版本后，历史结果仍保持当前版本。</span><span className="top-spacer">执行 {data.run.durationSeconds || '—'} 秒</span></div>
  <div className="grid grid-4 section-gap"><Metric label="已定位" value={counts.located} tone="green" /><Metric label="需澄清" value={counts.clarify} tone="amber" /><Metric label="证据缺口" value={counts.gap} tone="red" /><Metric label="字段总数" value={data.run.fieldResults.length} tone="blue" /></div>
  <div className="request-layout section-gap"><section className="panel"><div className="panel-head"><div><h2>字段来源清单</h2><p>选择字段查看右侧证据；结果类型、证据状态和定位状态分开表达。</p></div><StatusBadge label={data.request.status === 'needs_review' ? '有待复核项' : '已完成'} tone={data.request.status === 'needs_review' ? 'amber' : 'green'} /></div><div className="panel-body flush"><FieldResultTable results={data.run.fieldResults} selectedId={selected?.id} onSelect={setSelected} /></div></section><EvidencePanel field={selected} /></div>
  {feedback && <FeedbackDialog requestId={data.request.id} field={feedback} onClose={() => setFeedback(undefined)} onSubmitted={() => { setFeedback(undefined); setToast('反馈已进入知识复核队列。'); load() }} />}
  {selected && <div className="section-gap page-actions"><button className="btn quiet" type="button" onClick={() => setFeedback(selected)}>对“{selected.label}”提交反馈</button></div>}
  {toast && <div className="toast" role="status" onClick={() => setToast('')}>{toast}</div>}
  </>}</AsyncState>
}

function Metric({ label, value, tone }: { label: string; value: number; tone: 'green' | 'amber' | 'red' | 'blue' }) {
  return <article className="panel metric-card"><span>{label}</span><strong style={{ color: `var(--${tone})` }}>{value}</strong><small>当前执行结果</small></article>
}
