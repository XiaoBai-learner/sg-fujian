import { FormEvent, useState } from 'react'
import { submitFeedback } from '../services/mockService'
import type { FieldResult } from '../domain/types'

export default function FeedbackDialog({ requestId, field, onClose, onSubmitted }: { requestId: string; field: FieldResult; onClose: () => void; onSubmitted: () => void }) {
  const [verdict, setVerdict] = useState<'wrong' | 'needs_context'>('wrong')
  const [reason, setReason] = useState('')
  const [correction, setCorrection] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!reason.trim()) return
    setBusy(true)
    try { await submitFeedback({ requestId, fieldResultId: field.id, verdict, reason, correction }); onSubmitted() } finally { setBusy(false) }
  }
  return <div className="modal-backdrop" role="presentation"><form className="modal" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="feedback-title">
    <header className="modal-head"><div><h2 id="feedback-title">提交字段反馈</h2><p>{field.label} · 反馈会进入知识复核队列，不会直接改写线上版本。</p></div><button className="close" type="button" onClick={onClose} aria-label="关闭">×</button></header>
    <div className="modal-body form-grid">
      <div className="form-field"><label htmlFor="verdict">反馈类型</label><select id="verdict" value={verdict} onChange={event => setVerdict(event.target.value as typeof verdict)}><option value="wrong">来源不正确</option><option value="needs_context">需要补充页面上下文</option></select></div>
      <div className="form-field"><label htmlFor="reason">原因 <span className="version-pill">必填</span></label><textarea id="reason" value={reason} onChange={event => setReason(event.target.value)} placeholder="例如：这个页面显示的是缴费方式名称，不是渠道编码。" /></div>
      <div className="form-field"><label htmlFor="correction">建议答案（可选）</label><input id="correction" value={correction} onChange={event => setCorrection(event.target.value)} placeholder="可以填写正确字段或补充口径" /></div>
    </div>
    <footer className="modal-foot"><button className="btn quiet" type="button" onClick={onClose}>取消</button><button className="btn primary" type="submit" disabled={busy || !reason.trim()}>{busy ? '提交中…' : '提交复核'}</button></footer>
  </form></div>
}
