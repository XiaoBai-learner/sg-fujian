import { useEffect, useRef, useState } from 'react'
import Icon from '../../shared/Icon'
import { api, apiFetch } from '../../shared/api/session'
import { request, type LiveSnapshot } from '../modeling/live'
import type { Snapshot, TraceResult } from '../modeling/state'
import type { ModelEntry } from '../modeling/catalog'

type Attachment = { id: string; url: string; name: string; ocr_status: string }
export type Turn = { snapshotId?: string; id: string; question: string; modelName: string; version: number; results: TraceResult[]; attachments: Attachment[] }
export default function AgentPage({ turn, onTurn, onModel, initialModelId }: { turn?: Turn; onTurn: (turn: Turn) => void; onModel: () => void; initialModelId?: string | null }) {
  const [question, setQuestion] = useState('')
  const [models, setModels] = useState<ModelEntry[]>([])
  const [modelId, setModelId] = useState(initialModelId ?? '')
  const [active, setActive] = useState<Snapshot | null>(null)
  const [copied, setCopied] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const input = useRef<HTMLInputElement>(null)
  const selected = models.find(item => item.id === modelId)
  useEffect(() => {
    void api<{ items: ModelEntry[] }>('modeling/models').then(data => {
      const available = data.items.filter(model => model.adopted_id)
      setModels(available)
      setModelId(current => available.some(model => model.id === current) ? current : available[0]?.id ?? '')
    }).catch(error => setError(error.message))
  }, [])
  useEffect(() => {
    setActive(null)
    let alive = true
    if (modelId) void request<{ active: LiveSnapshot | null }>(`modeling/models/${modelId}`).then(detail => { if (alive) setActive(detail.active ? { ...detail.active, snapshotId: detail.active.id } : null) }).catch(error => { if (alive) setError(error.message) })
    return () => { alive = false }
  }, [modelId])
  const ask = async () => {
    if (!active?.snapshotId || !question.trim() || busy) return
    const fields = [...new Set(question.split(/[,，、；;\n]+/).map(field => field.trim()).filter(Boolean))]
    if (fields.length > 20 || fields.some(field => field.length > 200)) { setError('每次最多 20 个字段，每个字段不超过 200 字。'); return }
    setBusy(true); setError('')
    try {
      const result = await request<{ results: TraceResult[] }>('modeling/trace', { fields, snapshot_id: active.snapshotId, attachment_ids: attachments.map(item => item.id) })
      onTurn({ id: crypto.randomUUID(), question, modelName: selected?.name ?? '本体模型', version: active.version, snapshotId: active.snapshotId, results: result.results, attachments })
      setQuestion(''); setAttachments([])
    } catch (error) { setError(error instanceof Error ? error.message : '溯源失败') } finally { setBusy(false) }
  }
  const upload = async (file: File | undefined) => {
    if (!file) return
    if (attachments.length >= 5) { setError('每次最多上传 5 张截图。'); return }
    if (file.size > 5_000_000 || !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { setError('请上传 5 MB 以内的 PNG、JPEG 或 WebP。'); return }
    setBusy(true); setError('')
    try {
      const response = await apiFetch('/api/v1/modeling/attachments', { method: 'POST', headers: { 'Content-Type': file.type }, body: file })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail?.message || '截图上传失败')
      setAttachments(current => [...current, { ...data, name: file.name }])
    } catch (error) { setError(error instanceof Error ? error.message : '截图上传失败') } finally { setBusy(false); if (input.current) input.current.value = '' }
  }
  const renderResult = (result: TraceResult) => <article className="trace-result" key={result.field}>
    <div className="section-heading"><h3>{result.field}</h3><span className={`status-label ${result.status === 'located' ? 'available' : ''}`}>{result.status === 'located' ? '已定位' : result.status === 'ambiguous' ? '存在多个候选' : '未找到'}</span></div>
    <div className="confidence-line"><span>字段归属置信度</span><strong>{result.confidence == null ? '证据不足' : `${Math.round(result.confidence * 100)}%`}</strong><small>{result.confidence_label}</small></div>
    {result.confidence_basis && <p className="small-note">{result.confidence_basis}</p>}
    {result.sources.map(source => <div className="answer-source" key={source}><code>{source}</code><button className="text-button" onClick={async () => { try { await navigator.clipboard.writeText(source); setCopied(source) } catch { setCopied(`failed:${source}`) } }}>{copied === source ? '已复制' : copied === `failed:${source}` ? '复制失败' : '复制'}</button></div>)}
    {result.item?.expression && <div className="formula"><code>{result.item.expression}</code><p>{result.item.scope}</p></div>}
    {result.candidates?.map((candidate, index) => <div className="ambiguous-source" key={index}><strong>{candidate.item?.concept} / {candidate.item?.name}</strong>{candidate.sources.map(source => <code key={source}>{source}</code>)}</div>)}
    {result.status !== 'located' && <p className="small-note">请补充准确的字段名称或建模材料。候选仅来自所选模型已采用的本体与 R2RML。</p>}
    {result.item && <details className="trace-evidence"><summary>来源依据</summary>{result.item.evidence.map((evidence, index) => <blockquote key={index}><strong>{evidence.label}</strong><p>{evidence.quote}</p></blockquote>)}</details>}
  </article>
  return <section className={`agent-workspace ${turn ? 'has-results' : ''}`}><div className="agent-stage">
    {!turn ? <div className="agent-heading"><Icon name="trace" size={34} /><h1>查找字段的来源</h1><p>选择本体模型，输入字段或补充截图。</p></div> : <div className="conversation"><div className="question-bubble">{turn.question}{turn.attachments.map(item => <a key={item.id} href={item.url} target="_blank" rel="noreferrer"><img src={item.url} alt={item.name} /></a>)}</div><div className="answer-heading"><Icon name="trace" size={19} /><h2>字段溯源结果</h2><span className="subtle">{turn.modelName} · r{turn.version}</span></div>{turn.results.map(renderResult)}<p className="small-note">置信度是当前匹配证据的规则评分，尚未经过业务准确率校准。截图内容不参与自动识别。</p></div>}
    {!models.length && <div className="agent-empty-model"><Icon name="model" size={19} /><span>还没有可用于问答的已采用模型。</span><button className="text-button" onClick={onModel}>去本体建模<Icon name="arrow" size={14} /></button></div>}
    <form className="agent-composer" onSubmit={event => { event.preventDefault(); void ask() }}><label htmlFor="trace-question" className="visually-hidden">待溯源字段或问题</label><textarea id="trace-question" value={question} maxLength={2000} rows={3} onChange={event => setQuestion(event.target.value)} placeholder="输入字段名称，多个字段用逗号分隔…" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void ask() } }} />
      {!!attachments.length && <div className="attachment-list">{attachments.map(item => <div key={item.id}><img src={item.url} alt={item.name} /><span>{item.name}</span><button type="button" aria-label={`移除截图 ${item.name}`} onClick={() => setAttachments(current => current.filter(value => value.id !== item.id))}><Icon name="close" size={14} /></button></div>)}</div>}
      <div className="composer-toolbar"><button className="icon-button" title="上传截图" type="button" aria-label="上传截图" disabled={busy} onClick={() => input.current?.click()}><Icon name="image" size={20} /></button><input ref={input} type="file" accept="image/png,image/jpeg,image/webp" className="visually-hidden" tabIndex={-1} aria-label="选择截图文件" onChange={event => void upload(event.target.files?.[0])} /><label className="model-selector"><Icon name="model" size={16} /><select aria-label="选择溯源本体模型" value={modelId} onChange={event => setModelId(event.target.value)} disabled={busy || !models.length}>{!models.length && <option value="">未选择模型</option>}{models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}</select></label><span className="composer-spacer" /><small>{busy ? '正在处理…' : 'Enter 发送'}</small><button type="submit" className="send-button" aria-label="发送字段溯源" disabled={busy || !active || !question.trim()}><Icon name="up" size={20} /></button></div>
    </form>
    {!!attachments.length && <p className="small-note">截图已保存为本次附件。自动读图尚未接通，请同时输入字段名或粘贴客户提供的 OCR 文本；不会识别或发送截图中的样例行。</p>}
    {error && <p className="message error" role="alert">{error}</p>}<p className="agent-source-note">基于已采用的 OWL / R2RML 返回来源和依据。</p>
  </div></section>
}
