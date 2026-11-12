import { FormEvent, useState } from 'react'
import { createTraceRequest } from '../services/mockService'

const sampleFields = ['户号', '用户名称', '供电单位', '合同容量', '欠费月数', '应收金额', '实收金额', '欠费金额', '缴费渠道', '负荷率']

export default function NewRequestPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [title, setTitle] = useState('欠费客户清单字段溯源')
  const [description, setDescription] = useState('请确认欠费客户清单里的字段分别来自哪个系统、哪张原表和原表字段。')
  const [system, setSystem] = useState('营销业务应用 / 数据中台')
  const [page, setPage] = useState('客户服务 > 欠费客户清单')
  const [ocrText, setOcrText] = useState('欠费客户清单\\n户号  用户名称  供电单位  合同容量  欠费月数  应收金额  实收金额  欠费金额  缴费渠道  负荷率')
  const [fields, setFields] = useState(sampleFields)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const toggleField = (field: string) => setFields(current => current.includes(field) ? current.filter(item => item !== field) : [...current, field])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim() || !fields.length) { setError('请填写需求标题，并至少选择一个字段。'); return }
    setBusy(true); setError('')
    try {
      const request = await createTraceRequest({ title, description, system, page, ocrText, fields })
      onNavigate(`/requests/${request.id}`)
    } catch (e) { setError(e instanceof Error ? e.message : '创建需求失败') } finally { setBusy(false) }
  }
  return <><div className="page-head">
    <div><p className="page-kicker">FIELD TRACE / NEW REQUEST</p><h1>新建溯源需求</h1><p>先固定页面上下文和要查的字段，系统会把每次执行绑定到当前发布知识版本。</p></div>
    <div className="page-actions"><button className="btn" type="button" onClick={() => onNavigate('/workbench')}>返回工作台</button></div>
  </div>
  <form onSubmit={submit} className="grid grid-2">
    <section className="panel"><div className="panel-head"><div><h2>需求信息</h2><p>这些内容会进入执行记录，作为证据上下文。</p></div></div><div className="panel-body form-grid">
      <div className="form-field"><label htmlFor="title">需求标题</label><input id="title" value={title} onChange={event => setTitle(event.target.value)} maxLength={100} /></div>
      <div className="form-grid two"><div className="form-field"><label htmlFor="system">业务系统</label><input id="system" value={system} onChange={event => setSystem(event.target.value)} /></div><div className="form-field"><label htmlFor="page">页面路径</label><input id="page" value={page} onChange={event => setPage(event.target.value)} /></div></div>
      <div className="form-field"><label htmlFor="description">需求说明</label><textarea id="description" value={description} onChange={event => setDescription(event.target.value)} /></div>
      <div className="form-field"><label htmlFor="ocr">截图 OCR 文本</label><small>原始 OCR 文本只作为本次执行输入，不自动变成知识。</small><textarea id="ocr" value={ocrText} onChange={event => setOcrText(event.target.value)} /></div>
      {error && <div className="notice danger" role="alert">{error}</div>}
      <div className="page-actions"><button className="btn quiet" type="button" onClick={() => onNavigate('/workbench')}>取消</button><button className="btn primary" type="submit" disabled={busy}>{busy ? '提交中…' : '提交并开始溯源'}</button></div>
    </div></section>
    <section className="panel"><div className="panel-head"><div><h2>选择字段</h2><p>可从 OCR 表头中调整，未选字段不会进入本次结果。</p></div><span className="version-pill">{fields.length} / 40</span></div><div className="panel-body check-list">
      {sampleFields.map(field => <label className="check-option" key={field}><input type="checkbox" checked={fields.includes(field)} onChange={() => toggleField(field)} /><span><b>{field}</b><small>{field === '欠费金额' ? '计算字段 · 需要展示公式和过滤条件' : field === '负荷率' ? '当前版本证据不足时会明确拒答' : '按本体、映射和页面血缘检索'}</small></span></label>)}
    </div></section>
  </form></>
}
