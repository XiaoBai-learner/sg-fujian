import { useState } from 'react'
import Icon from '../../shared/Icon'
import { request } from '../modeling/live'
import { tracePreview, type Snapshot, type TraceResult } from '../modeling/preview'

export type Turn = { snapshotId?: string; id: string; question: string; version: number; results: TraceResult[] }
export default function AgentPage({ active, turn, onTurn, onModel }: {
  active: Snapshot | null; turn?: Turn; onTurn: (turn: Turn) => void; onModel: () => void
}) {
  const [question, setQuestion] = useState('')
  const [copied, setCopied] = useState('')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const ask = async (text = question) => {
    if (!active || !text.trim() || busy) return
    const fields = [...new Set(text.split(/[,，、；;\n]+/).map(field => field.trim()).filter(Boolean))].slice(0, 20)
    setBusy(true);setError('')
    try {
      const result = active.snapshotId ? await request<{results:TraceResult[]}>('modeling/trace',{fields,snapshot_id:active.snapshotId}) : {results:fields.map(field => tracePreview(active, field))}
      onTurn({id:crypto.randomUUID(),question:text,version:active.version,snapshotId:active.snapshotId,results:result.results});setQuestion('')
    } catch (error) {setError(error instanceof Error ? error.message : '溯源失败')} finally {setBusy(false)}
  }
  return <section className={`agent-workspace ${turn ? 'has-results' : ''}`}>
    <div className="agent-stage">
      {!turn ? <div className="agent-heading"><span className="agent-symbol"><Icon name="trace" size={38} /></span>
        <div className="eyebrow">字段溯源智能体</div><h1>从业务字段，找到数据源头</h1><p>基于已采用的本体与映射，每一个答案都有依据。</p></div> :
        <div className="conversation"><div className="question-bubble">{turn.question}</div>
          <div className="answer-heading"><span className="tiny-icon blue"><Icon name="trace" size={17} /></span><h2>字段来源</h2><span className="badge purple">{turn.snapshotId ? '模型' : '示例模型'} r{turn.version}</span></div>
          {(active?.snapshotId !== turn.snapshotId || active?.version !== turn.version) && <p className="message info">这条记录保留当时的模型 v{turn.version}，新提问使用当前版本。</p>}
          {turn.results.map(result => <article className="trace-result" key={result.field}>
            <div className="section-heading"><h3>{result.field}</h3><span className={`badge ${result.status !== 'located' ? 'amber' : result.kind === 'calculated' ? 'purple' : 'mint'}`}>
              {result.status !== 'located' ? '未确认来源' : result.kind === 'calculated' ? '计算字段' : '已定位'}</span></div>
            {result.item && <p className="trace-concept">{result.item.concept} / {result.item.name}</p>}
            {result.sources.map(source => <div className="answer-source" key={source}><code>{source}</code><button className="text-button" onClick={async () => {
              try { await navigator.clipboard.writeText(source); setCopied(source) } catch { setCopied(`failed:${source}`) }
            }}>{copied === source ? '已复制' : copied === `failed:${source}` ? '复制失败' : '复制'}</button></div>)}
            {result.item?.expression && <div className="formula"><code>{result.item.expression}</code><p>{result.item.scope}</p></div>}
            {result.status !== 'located' && <p>当前采用版本没有明确来源。请补充页面信息或建模材料；不会使用 DDL 中未经采用的字段替代回答。</p>}
            {result.item && <details className="trace-evidence"><summary>查看来源依据<span>本体属性 → 来源映射 → 物理列</span></summary>
              {result.item.evidence.map((evidence, index) => <blockquote key={index}><strong>{evidence.label}</strong><p>{evidence.quote}</p></blockquote>)}</details>}
          </article>)}
        </div>}
      {!active && <div className="agent-onboarding"><span className="round-icon purple"><Icon name="model" /></span><div><strong>先让材料形成可用的本体</strong>
        <p>传入 DDL、SQL 与文档，生成并检查模型后，就可以在这里溯源。</p></div>
        <button className="button secondary" onClick={onModel}>去建模<Icon name="arrow" size={16} /></button></div>}
      <div className="composer-context"><button onClick={onModel}><Icon name="model" size={17} />营销域本体
        <span>{active ? `${active.snapshotId ? '模型' : '示例'} r${active.version}` : '未采用'}</span><Icon name="chevron" size={14} /></button><small>OWL + R2RML</small></div>
      <form className="agent-composer" onSubmit={event => { event.preventDefault(); ask() }}>
        <label htmlFor="trace-question" className="visually-hidden">待溯源的字段名称</label>
        <textarea id="trace-question" value={question} maxLength={2000} rows={3} onChange={event => setQuestion(event.target.value)}
          placeholder="输入字段名，如：户号、客户名称、欠费金额"
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); ask() } }} />
        <div><span><Icon name="file" size={17} />多个字段可用逗号分隔</span><small>Enter 发送</small>
          <button type="submit" className="send-button" aria-label="发送字段溯源" disabled={busy || !active || !question.trim()}><Icon name="up" size={21} /></button></div>
      </form>
      {!turn && <div className="suggested-fields">{['户号', '欠费金额', '联系电话'].map(field => <button key={field} disabled={!active} onClick={() => ask(field)}>{field}<Icon name="arrow" size={15} /></button>)}</div>}
      {error && <p className="message error" role="alert">{error}</p>}<p className="agent-preview-note">{active?.snapshotId ? '候选来源为已采用 OWL / R2RML；派生字段依赖经导出映射核对。' : '示例模式使用本地合成映射。'}</p>
    </div>
    <p className="agent-footnote">每一个字段，都有据可循。</p>
  </section>
}
