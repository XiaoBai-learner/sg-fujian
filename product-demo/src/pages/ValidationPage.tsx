import { useEffect, useState } from 'react'
import { AsyncState } from '../components/AsyncState'
import StatusBadge from '../components/StatusBadge'
import { getKnowledgeOverview, runValidation } from '../services/mockService'
import type { KnowledgeOverview, ValidationRun } from '../domain/types'

export default function ValidationPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [overview, setOverview] = useState<KnowledgeOverview>()
  const [validation, setValidation] = useState<ValidationRun>()
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = () => { setLoading(true); getKnowledgeOverview().then(next => { setOverview(next); setValidation(next.validation) }).catch(e => setError(e instanceof Error ? e.message : '验证状态读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [])
  const execute = async () => {
    setBusy(true)
    if (validation) setValidation({ ...validation, status: 'running' })
    try { setValidation(await runValidation()) } catch (e) { setError(e instanceof Error ? e.message : '验证失败') } finally { setBusy(false) }
  }
  return <AsyncState loading={loading} error={error} onRetry={load}>{overview && validation && <><div className="page-head"><div><p className="page-kicker">KNOWLEDGE WORKSPACE / VALIDATION</p><h1>验证与试问</h1><p>验证中心把结构、来源、业务口径和回归结果集中展示，未通过项不会被包装成已发布能力。</p></div><div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/knowledge/model')}>返回模型</button><button className="btn primary" type="button" disabled={busy} onClick={execute}>{busy ? '验证中…' : '运行全部验证'}</button></div></div>
    <div className="stepper section-gap">{['结构验证', '来源验证', '业务验证', '问答回归'].map((label, index) => <div className={`step ${index < 3 ? 'done' : 'current'}`} key={label}><span className="step-number">{index + 1}</span>{label}</div>)}</div>
    <div className="grid grid-2 section-gap"><section className="panel"><div className="panel-head"><div><h2>验证结果</h2><p>每项检查都有明确状态和责任范围。</p></div><StatusBadge label={validation.status === 'running' ? '执行中' : '已完成'} tone={validation.status === 'running' ? 'amber' : 'green'} /></div><div className="panel-body grid">{validation.checks.map(check => <div className="notice" key={check.id}><StatusBadge label={check.status === 'passed' ? '通过' : check.status === 'warning' ? '提示' : '失败'} tone={check.status === 'passed' ? 'green' : check.status === 'warning' ? 'amber' : 'red'} /><span><strong>{check.label}</strong><br />{check.detail}</span>{typeof check.count === 'number' && <span className="top-spacer mono">{check.count}</span>}</div>)}</div></section><section className="panel"><div className="panel-head"><div><h2>回归试问</h2><p>固定一批已审核案例，检查候选版本是否改变结果。</p></div><StatusBadge label={`${validation.regression.passed}/${validation.regression.total} 通过`} tone="green" /></div><div className="panel-body"><dl className="detail-kv"><dt>通过</dt><dd>{validation.regression.passed} 个字段结果保持一致</dd><dt>变化</dt><dd>{validation.regression.changed} 个字段状态变化，需要审核说明</dd><dt>结论</dt><dd>{validation.message}</dd></dl><div className="notice warn section-gap"><span><strong>试问不会改变线上答案</strong><br />执行结果固定候选版本，发布前可与当前版本对比。</span></div></div></section></div>
  </>}</AsyncState>
}
