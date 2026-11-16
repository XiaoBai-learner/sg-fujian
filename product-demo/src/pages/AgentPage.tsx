import { useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import type { Page, Result, Turn, Workspace } from '../domain/types'
import { extractFields, traceFields } from '../services/workspace'
import Icon from '../components/Icon'

const suggestions = ['户号来自哪个字段？', '欠费金额怎么算？', '欠费客户怎么认定的？']

export default function AgentPage({ state, onChange, onNavigate }: {
  state: Workspace; onChange: Dispatch<SetStateAction<Workspace>>; onNavigate: (page: Page) => void
}) {
  const [question, setQuestion] = useState('')
  const [ocr, setOcr] = useState('')
  const [showOcr, setShowOcr] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Turn | undefined>()
  const activeTurn = selected ? state.turns.find(turn => turn.id === selected.id) : state.turns.at(-1)
  const ask = async (text = question) => {
    if (busy || (!text.trim() && !ocr.trim())) return
    const labels = extractFields(text, ocr, state)
    if (!labels.length) { setError('请在问题中写出字段名，或补充截图表头。'); return }
    setBusy(true); setError('')
    try {
      // 短暂延迟仅展示原型的查询反馈；结果来自本地已应用的模型快照。
      await new Promise(resolve => setTimeout(resolve, 450))
      const turn: Turn = { id: crypto.randomUUID(), question: text.trim() || '请溯源截图中的字段', ocr, revision: state.active.revision, results: traceFields(state, labels) }
      onChange(current => ({ ...current, turns: [...current.turns, turn] })); setSelected(undefined); setQuestion(''); setOcr(''); setShowOcr(false)
    } catch { setError('这次查询未完成，请重试。') } finally { setBusy(false) }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void ask() }
  return <div className={`agent-workspace ${activeTurn ? 'has-results' : ''}`}>
    <div className="agent-context"><span className="status-label good"><i />营销域本体 v{state.active.revision}</span><span>基于本体与 R2RML 映射</span><button className="text-action" onClick={() => onNavigate('modeling')}>查看模型 ↗</button></div>
    <div className="agent-heading"><span className="agent-emblem"><Icon name="agent" /></span><h1>{activeTurn ? '字段溯源' : '这个字段，来自哪里？'}</h1><p>问一个业务字段，或粘贴截图文本，找到它的原表、原字段和依据。</p></div>
    {activeTurn && <section className="conversation">
      <div className="question-bubble"><span>你</span><p>{activeTurn.question}</p>{activeTurn.ocr && <details><summary>截图文本</summary><pre>{activeTurn.ocr}</pre></details>}</div>
      <div className="answer-heading"><Icon name="agent" /><strong>来源结果</strong><span>本体 v{activeTurn.revision}</span><button className="text-action" onClick={() => { setSelected(undefined); onChange({ ...state, turns: [] }) }}>新对话</button></div>
      {activeTurn.revision !== state.active.revision && <p className="inline-note">本条结果使用旧模型 v{activeTurn.revision}。可再次提问，使用当前 v{state.active.revision} 分析。</p>}
      <div className="result-list">{activeTurn.results.map((result, i) => <ResultCard key={`${result.label}-${i}`} result={result} />)}</div>
    </section>}
    <form className="question-form" onSubmit={submit}>
      {showOcr && <div className="ocr-input"><div><label htmlFor="ocr-text">截图 OCR 文本</label><button type="button" className="text-action" onClick={() => setOcr('客户档案查询\n户号  用户名称  合同容量\n示例编号  示例客户  120')}>填入示例</button></div><textarea id="ocr-text" maxLength={20000} rows={5} placeholder="粘贴客户侧 OCR 输出，不需要上传图片" value={ocr} onChange={e => setOcr(e.target.value)} /></div>}
      <label className="sr-only" htmlFor="question">字段溯源问题</label><textarea id="question" rows={2} maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void ask() } }} placeholder="例如：户号和应收电费分别来自哪张表？" />
      <div className="composer-actions"><button type="button" className={`text-action ${showOcr ? 'selected' : ''}`} aria-expanded={showOcr} onClick={() => setShowOcr(!showOcr)}><Icon name="plus" />截图文本</button><span>Enter 发送 · Shift + Enter 换行</span><button type="submit" className="send-button" disabled={busy || (!question.trim() && !ocr.trim())} aria-label="发送问题">{busy ? '查询中' : <Icon name="arrow" />}</button></div>
    </form>
    {error && <p className="error-note" role="alert">{error}</p>}
    {!activeTurn && <div className="suggested-questions">{suggestions.map(text => <button key={text} onClick={() => void ask(text)} disabled={busy}>{text}<span>↗</span></button>)}</div>}
    {busy && <p className="thinking" role="status">正在匹配本体属性与来源映射…</p>}
    {state.turns.length > 1 && <div className="recent-turns"><span>最近提问</span>{state.turns.slice(-4).reverse().map(turn => <button key={turn.id} className="text-action" onClick={() => setSelected(turn)}>{turn.question}</button>)}</div>}
    <p className="agent-footnote">结果以来源证据为准。当前为本地交互原型，未连接大模型与生产数据。</p>
  </div>
}

function ResultCard({ result }: { result: Result }) {
  return <article className="result-card">
    <div className="result-title"><h2>{result.label}</h2><span className={`result-status ${result.status}`}>{result.status === 'not_found' ? '未找到' : result.status === 'ambiguous' ? '多个候选' : result.kind === 'rule' ? '规则解释' : result.kind === 'calculated' ? '计算字段' : '已定位'}</span></div>
    {result.rule && <p className="rule-text">{result.rule}</p>}
    {result.calculation && <div className="calculation"><code>{result.calculation.formula}</code><small>条件：{result.calculation.filters.join('，')}</small></div>}
    {result.sources.map(source => <div className="answer-source" key={source.column}><code>{source.column}</code><span>{source.concept} · {source.label}</span><button type="button" className="text-action" onClick={async e => { const button = e.currentTarget; try { await navigator.clipboard.writeText(source.column); button.textContent = '已复制' } catch { button.textContent = '复制失败' } }}>复制</button></div>)}
    {result.status === 'not_found' && <p className="not-found-text">当前本体与映射中没有找到可信的源字段。</p>}
    {result.status === 'ambiguous' && <p className="not-found-text">请补充系统或页面上下文，进一步确认实际来源。</p>}
    <details className="answer-evidence"><summary>查看来源依据 <span>本体属性 → R2RML → 源字段</span></summary><ul>{result.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></details>
  </article>
}
