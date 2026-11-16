import { useRef, useState, type Dispatch, type SetStateAction } from 'react'
import type { Workspace } from '../domain/types'
import { adoptModelPreview, collectModelingInputs, generateModelPreview, readModelingFiles, type ModelPreview } from '../services/modeling'
import { materials as examples } from '../services/seed'
import Icon from './Icon'

export default function ModelingMaterials({ state, onChange, onAdopt }: {
  state: Workspace; onChange: Dispatch<SetStateAction<Workspace>>; onAdopt: () => void
}) {
  const inputs = collectModelingInputs(state)
  const selected = state.modeling?.selected ?? inputs.filter(input => input.ready && (input.kind === 'DDL' || input.kind === '结构快照' || input.kind === '业务说明')).map(input => input.id)
  const [preview, setPreview] = useState<ModelPreview>()
  const [inspected, setInspected] = useState('')
  const [pasted, setPasted] = useState('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const inspectedInput = inputs.find(input => input.id === inspected)
  const select = (id: string, checked: boolean) => {
    onChange(current => ({ ...current, modeling: { selected: checked ? [...selected, id] : selected.filter(value => value !== id) } }))
    setPreview(undefined); setError('')
  }
  const addFiles = async (files: File[]) => {
    if (!files.length) return
    setBusy(true); setError(''); setNotice('')
    try {
      const added = await readModelingFiles(files)
      onChange(current => ({ ...current, materials: [...current.materials, ...added],
        modeling: { selected: [...selected, ...added.filter(material => material.text?.trim()).map(material => `material:${material.id}`)] } }))
      setPreview(undefined); setPasted('')
      setNotice(added.some(material => !material.text) ? 'PDF 已登记，等待后端解析；文本材料已在本地读取。' : `已读取 ${added.length} 份材料，已选用于本次建模。`)
    } catch (error) { setError(error instanceof Error ? error.message : '材料读取失败，请重试。') }
    finally { setBusy(false) }
  }
  const generate = () => {
    setError(''); setNotice('')
    try { setPreview(generateModelPreview(state, selected)); setInspected('') }
    catch (error) { setPreview(undefined); setError(error instanceof Error ? error.message : '本地预览未完成。') }
  }
  const adopt = () => {
    if (!preview) return
    try {
      onChange(adoptModelPreview(state, preview))
      onAdopt()
    } catch (error) { setError(error instanceof Error ? error.message : '无法采用这份预览。') }
  }
  const addExample = () => {
    const example = structuredClone(examples.find(material => material.id === 'business-doc')!)
    onChange(current => ({ ...current, materials: [...current.materials, example], modeling: { selected: [...selected, `material:${example.id}`] } }))
    setPreview(undefined)
  }
  return <section className="model-material-workspace" aria-label="建模材料与生成">
    <div className="model-input-panel">
      <div className="model-panel-heading"><div><h2>建模材料</h2><p>文档与 DDL，统一选用。</p></div><button className="action primary" onClick={generate} disabled={!selected.length || busy}><Icon name="spark" />生成本体草稿</button></div>
      <button className={`material-dropzone${dragging ? ' is-dragging' : ''}`} disabled={busy}
        onClick={() => fileInput.current?.click()}
        onDragOver={event => { event.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={event => { event.preventDefault(); setDragging(false); if (!busy) void addFiles([...event.dataTransfer.files]) }}>
        <span className="upload-mark"><Icon name="upload" /></span><strong>拖拽文档或 DDL 到这里</strong><span>或点击选择文件</span><small>TXT / Markdown / SQL / PDF · 每份最多 1 MB</small>
      </button>
      <input type="file" accept=".txt,.md,.sql,.pdf" multiple hidden ref={fileInput} onChange={event => { void addFiles([...event.target.files || []]); event.target.value = '' }} />
      <details className="paste-material"><summary>或粘贴文档正文 / DDL</summary><label className="sr-only" htmlFor="model-material-text">建模材料正文</label><textarea id="model-material-text" rows={5} maxLength={100000} value={pasted} placeholder="粘贴业务说明、字段口径或 CREATE TABLE…" onChange={event => setPasted(event.target.value)} /><button className="action" disabled={!pasted.trim() || busy} onClick={() => void addFiles([new File([pasted], /^\s*(?:CREATE\s+TABLE|USE\s)/i.test(pasted) ? '粘贴的结构.sql' : '粘贴的业务说明.md')])}>添加到材料库</button></details>
      <div className="input-group-heading"><span>可选材料 <small>{inputs.length} · 已选 {selected.length} 份</small></span>{!state.materials.some(material => material.id === 'business-doc') && <button className="text-action" onClick={addExample}>使用示例文档</button>}</div>
      <div className="model-input-list">{inputs.map(input => <div className={`model-input-row${selected.includes(input.id) ? ' is-selected' : ''}`} key={input.id}>
        <label><input type="checkbox" checked={selected.includes(input.id)} disabled={!input.ready || busy} onChange={event => select(input.id, event.target.checked)} />
          <span className={`material-type-icon ${input.kind === '结构快照' || input.kind === 'DDL' ? 'is-schema' : ''}`}><Icon name={input.kind === '结构快照' ? 'source' : 'file'} /></span>
          <span className="model-input-info"><strong>{input.name}</strong><span><b>{input.kind}</b><span className={input.ready ? 'input-ready' : 'input-pending'}>{input.ready ? input.tables.length ? `${input.tables.length} 张表 · 可用` : '正文已读取' : /\.pdf$/i.test(input.name) ? '待后端解析' : '仅登记，需补充正文'}</span></span></span>
        </label><button className="icon-button" aria-label={`查看材料 ${input.name}`} title="查看材料正文" onClick={() => setInspected(inspected === input.id ? '' : input.id)}><Icon name="chevron" /></button>
      </div>)}</div>
      <p className="material-help">文本与基本 DDL 可在本地预览。PDF 待后端解析；文档识别暂使用营销域示例词汇。</p>
      {notice && <p className="success-note" role="status">{notice}</p>}
      {error && <p className="error-note" role="alert">{error}</p>}
    </div>
    <div className="model-output-panel">
      {inspectedInput ? <>
        <div className="model-panel-heading"><div><h2>材料正文</h2><p>{inspectedInput.name}</p></div><button className="icon-button" aria-label="关闭材料正文" onClick={() => setInspected('')}><Icon name="close" /></button></div>
        {inspectedInput.text ? <pre className="material-body">{inspectedInput.text}</pre> : <div className="model-empty-state"><Icon name="file" /><h3>这份材料还没有可用正文</h3><p>PDF 需要后端解析。也可以先粘贴已有的文本内容。</p></div>}
      </> : preview ? <>
        <div className="model-panel-heading"><div><h2>本体草稿预览</h2><p>核对来源与业务语义，再追加到编辑器。</p></div><span className="draft-preview-tag">待确认</span></div>
        <div className="preview-counts"><span><strong>{preview.model.concepts.length}</strong> 对象</span><span><strong>{preview.model.attributes.length}</strong> 属性</span><span><strong>{preview.model.relations.length}</strong> 关系</span></div>
        <div className="preview-concepts">{preview.model.concepts.map(concept => <article key={String(concept.id)}>
          <div><span className="preview-concept-dot" /><h3>{String(concept.name)}</h3><code>{String(concept.english_name || concept.id)}</code></div>
          <p>{preview.model.attributes.filter(attribute => attribute.concept_id === concept.id).map(attribute => <span key={attribute.id}>{attribute.name}</span>)}</p>
          <small><Icon name="file" />{[...new Set(preview.model.annotations.filter(annotation => annotation.subject === concept.id).map(annotation => String(annotation.value)))].join('、')}</small>
        </article>)}</div>
        {preview.model.relations.length > 0 && <div className="preview-relations"><h3>识别的关系</h3>{preview.model.relations.map(relation => <p key={String(relation.id)}>{String(preview.model.concepts.find(concept => concept.id === relation.source_id)?.name)}<span>— {String(relation.name)} →</span>{String(preview.model.concepts.find(concept => concept.id === relation.target_id)?.name)}</p>)}</div>}
        {preview.warnings.map(warning => <p className="inline-note" key={warning}>{warning}</p>)}
        <div className="preview-adopt"><span>已有定义保留，生成结果先进入草稿。</span><button className="action primary" onClick={adopt}><Icon name="check" />追加到当前草稿</button></div>
      </> : <div className="model-empty-state"><div className="model-empty-symbol"><Icon name="file" /><Icon name="arrow" /><Icon name="model" /></div><h3>让材料成为本体的起点</h3><p>选择业务文档、接入的 DDL 或结构快照，<br />生成对象、属性和关系的草稿预览。</p><div className="material-flow"><span>选择材料</span><Icon name="chevron" /><span>生成草稿</span><Icon name="chevron" /><span>编辑与映射</span></div><small>当前模型保留在“对象与属性”等页签中。</small></div>}
    </div>
  </section>
}
