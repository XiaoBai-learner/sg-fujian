import { useRef, useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import type { Material, WorkspaceAction, WorkspaceState } from './state'

export function MaterialInput({ state, dispatch, compact = false }: {
  state: WorkspaceState; dispatch: Dispatch<WorkspaceAction>; compact?: boolean
}) {
  const input = useRef<HTMLInputElement>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [text, setText] = useState('')
  const [dragging, setDragging] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const readFiles = async (files: File[]) => {
    if (busy || !files.length) return
    setError(''); setBusy(true)
    try {
      const materials: Material[] = []
      for (const file of files) {
        if (!/\.(sql|txt|md|pdf)$/i.test(file.name)) throw new Error(`${file.name}：请使用 SQL、TXT、Markdown 或文本 PDF。`)
        if (file.size > 2 * 1024 * 1024) throw new Error(`${file.name}：每份材料最多 2 MB。`)
        const pdf = /\.pdf$/i.test(file.name)
        let body = ''
        if (!pdf) {
          try { body = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()) }
          catch { throw new Error(`${file.name}：请使用 UTF-8 编码。`) }
          if (!body.trim() || body.includes('\0')) throw new Error(`${file.name}：没有可用的文本正文。`)
        }
        materials.push({ id: crypto.randomUUID(), name: file.name, size: file.size, body, origin: 'upload',
          kind: pdf ? 'PDF' : /\.sql$/i.test(file.name) ? /\bCREATE\s+TABLE\b/i.test(body) ? 'DDL' : '热点 SQL' : '业务说明' })
      }
      dispatch({ type: 'add-materials', materials }); setText('')
    } catch (error) { setError(error instanceof Error ? error.message : '材料读取失败，请重试。') }
    finally { setBusy(false); if (input.current) input.current.value = '' }
  }
  return <div className={`material-input ${compact ? 'compact' : ''}`}>
    <div className={`upload-zone ${dragging ? 'dragging' : ''}`}
      onDragOver={event => { event.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={event => { event.preventDefault(); setDragging(false); void readFiles([...event.dataTransfer.files]) }}>
      <span className="upload-icon"><Icon name="upload" size={26} /></span>
      <h2>把建模材料放进来</h2>
      <p>DDL、常用 SQL、字段说明、业务文档<br />一次选用，无需预先整理成本体。</p>
      <button className="button primary" onClick={() => input.current?.click()} disabled={busy}>
        <Icon name="plus" size={17} />{busy ? '正在读取…' : '选择材料'}
      </button>
      <input ref={input} type="file" className="visually-hidden" tabIndex={-1} accept=".sql,.txt,.md,.pdf" multiple
        aria-label="选择建模材料" onChange={event => void readFiles([...event.target.files ?? []])} />
      <small>支持拖拽 · SQL / TXT / MD / PDF · 每份 2 MB</small>
    </div>
    <div className="material-library">
      <div className="section-heading"><h2>本次使用的材料<span>{state.materials.length}</span></h2>
        <span className="subtle">{state.selected.length} 份已选</span></div>
      {!state.materials.length ? <div className="material-empty"><Icon name="folder" size={28} />
        <p>还没有建模材料</p><span>上传你的 DDL、SQL 或业务文档开始建模</span></div> :
        <ul className="material-list">{state.materials.map(material => <li key={material.id}>
          <div className={`material-row ${state.selected.includes(material.id) ? 'selected' : ''}`}>
            <label>
              <input type="checkbox" checked={state.selected.includes(material.id)}
                onChange={() => dispatch({ type: 'toggle-material', id: material.id })} />
              <span className={`file-icon ${material.kind === 'DDL' || material.kind.includes('SQL') ? 'blue' : 'purple'}`}>
                <Icon name={material.kind.includes('SQL') || material.kind === 'DDL' ? 'code' : 'file'} />
              </span>
              <span className="material-label"><strong>{material.name}</strong><small>{material.kind} · {Math.max(1, Math.ceil(material.size / 1024))} KB
                <span>
                  {material.kind === 'PDF' ? '待后端解析' : material.remoteRevision ? '已保存 · r'+material.remoteRevision : '正文已读取'}
                </span></small></span>
            </label>
            <button className="icon-button" aria-label={`查看 ${material.name}`} aria-expanded={expanded === material.id}
              onClick={() => setExpanded(expanded === material.id ? null : material.id)}><Icon name="chevron" /></button>
          </div>
          {expanded === material.id && <pre className="material-text">{material.body || 'PDF 已登记；文本提取服务尚未接通。不提供 OCR。'}</pre>}
        </li>)}</ul>}
      <details className="paste-input"><summary>也可以直接粘贴 DDL、SQL 或文档正文</summary>
        <label htmlFor="material-body">材料正文</label>
        <textarea id="material-body" rows={5} maxLength={200000} value={text}
          onChange={event => setText(event.target.value)} placeholder="CREATE TABLE… 或粘贴原始 SQL、业务说明" />
        <button className="button secondary" disabled={!text.trim() || busy} onClick={() => void readFiles([
          new File([text], /\bCREATE\s+TABLE\b/i.test(text) || /\bSELECT\b/i.test(text) ? '粘贴材料.sql' : '粘贴材料.md'),
        ])}>加入材料</button>
      </details>
      {error && <p role="alert" className="message error">{error}</p>}
      <p className="material-boundary"><Icon name="info" size={15} />文本材料会保存到后端并参与真实解析；PDF 请先转换为正文。</p>
    </div>
  </div>
}
