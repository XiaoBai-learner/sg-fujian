import { useEffect, useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import type { Page, Result, Turn, Workspace } from '../domain/types'
import { extractFields, traceFields } from '../services/workspace'
import Icon from '../components/Icon'

const suggestions = ['户号来自哪个字段？', '欠费金额怎么算？', '欠费客户怎么认定的？']

export default function AgentPage({ state, activeTurnId, onSelectTurn, onChange, onNavigate }: {
  state: Workspace; activeTurnId: string | null; onSelectTurn: (id: string) => void; onChange: Dispatch<SetStateAction<Workspace>>; onNavigate: (page: Page) => void
}) {
  const [question, setQuestion] = useState('')
  const [ocr, setOcr] = useState('')
  const [showOcr, setShowOcr] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const activeTurn = state.turns.find(turn => turn.id === activeTurnId)
  const questionInput = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { if (!activeTurnId) questionInput.current?.focus() }, [activeTurnId])
  const ask = async (text = question) => {
    if (busy || (!text.trim() && !ocr.trim())) return
    const labels = extractFields(text, ocr, state)
    if (!labels.length) { setError('请在问题中写出字段名，或补充截图表头。'); return }
    setBusy(true); setError('')
    try {
      // 短暂延迟仅展示原型的查询反馈；结果来自本地已应用的模型快照。
      await new Promise(resolve => setTimeout(resolve, 450))
      const turn: Turn = { id: crypto.randomUUID(), question: text.trim() || '请溯源截图中的字段', ocr, revision: state.active.revision, results: traceFields(state, labels) }
      onChange(current => ({ ...current, turns: [...current.turns, turn] })); onSelectTurn(turn.id); setQuestion(''); setOcr(''); setShowOcr(false)
    } catch { setError('这次查询未完成，请重试。') } finally { setBusy(false) }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void ask() }
  return <div className={`agent-workspace ${activeTurn ? 'has-results' : 'is-empty'}`}>
    <div className="agent-stage">
    {!activeTurn && <div className="agent-heading"><div className="agent-title"><Icon name="trace" /><h1>从业务字段，找到数据源头</h1></div><p>告诉我你想找的字段，剩下的交给本体与映射。</p></div>}
    {activeTurn && <section className="conversation">
      <div className="question-bubble"><p>{activeTurn.question}</p>{activeTurn.ocr && <details><summary>截图文本</summary><pre>{activeTurn.ocr}</pre></details>}</div>
      <div className="answer-heading"><span className="answer-mark"><Icon name="trace" /></span><strong>字段来源</strong><span>本体 v{activeTurn.revision}</span></div>
      {activeTurn.revision !== state.active.revision && <p className="inline-note">本条结果使用旧模型 v{activeTurn.revision}。可再次提问，使用当前 v{state.active.revision} 分析。</p>}
      <div className="result-list">{activeTurn.results.map((result, i) => <ResultCard key={`${result.label}-${i}`} result={result} />)}</div>
    </section>}
    <div className="composer-area">
    <div className="composer-context"><button title="查看当前使用的本体模型" onClick={() => onNavigate('modeling')}><Icon name="model" /><span>营销域本体</span><small>v{state.active.revision}</small><Icon name="chevron" /></button><span>本体 + R2RML</span></div>
    <form className={`question-form${busy ? ' is-busy' : ''}`} onSubmit={submit}>
      {showOcr && <div className="ocr-input"><div><label htmlFor="ocr-text">截图 OCR 文本</label><button type="button" className="text-action" onClick={() => setOcr('客户档案查询\n户号  用户名称  合同容量\n示例编号  示例客户  120')}>填入示例</button></div><textarea id="ocr-text" maxLength={20000} rows={5} placeholder="粘贴客户侧 OCR 输出，不需要上传图片" value={ocr} onChange={e => setOcr(e.target.value)} /></div>}
      <label className="sr-only" htmlFor="question">字段溯源问题</label><textarea ref={questionInput} id="question" rows={2} maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void ask() } }} placeholder={activeTurn ? '继续查找其他字段，或补充页面上下文…' : '想查哪个字段？也可以粘贴一段取数需求…'} />
      <div className="composer-actions"><button type="button" className={`add-context${showOcr ? ' selected' : ''}`} title="添加截图 OCR 文本" aria-label="添加截图 OCR 文本" aria-expanded={showOcr} onClick={() => setShowOcr(!showOcr)}><Icon name={showOcr ? 'close' : 'plus'} /></button><button type="button" className="context-action" aria-expanded={showOcr} onClick={() => setShowOcr(!showOcr)}><Icon name="file" />截图文本</button><span className="keyboard-hint">Enter 发送</span><button type="submit" className="send-button" disabled={busy || (!question.trim() && !ocr.trim())} aria-label="发送问题">{busy ? <span className="send-spinner" /> : <Icon name="up" />}</button></div>
    </form>
    </div>
    {error && <p className="error-note" role="alert">{error}</p>}
    {!activeTurn && <div className="suggested-questions">{suggestions.map(text => <button key={text} onClick={() => void ask(text)} disabled={busy}>{text}<Icon name="arrow" /></button>)}</div>}
    {busy && <p className="thinking" role="status">正在匹配本体属性与来源映射…</p>}
    </div>
    <p className="agent-footnote">每一个字段，都有据可循。<span>本地模型检索预览</span></p>
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
