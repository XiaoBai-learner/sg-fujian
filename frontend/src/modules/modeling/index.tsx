import { useEffect, useState } from 'react'
import Icon from '../../shared/Icon'
import Dialog from '../../shared/Dialog'
import MaterialPicker from './MaterialPicker'
import OntologyExplorer from './OntologyExplorer'
import ModelResults from './ModelResults'
import Validation from './Validation'
import useModelingWorkspace from './useModelingWorkspace'
import { request } from './live'
import type { ModelEntry } from './catalog'

export type StudioSection = 'materials' | 'ontology' | 'validation'
export default function ModelingPage({ id, onBack, onTrace, onSources, section, setSection }: { id: string; onBack: () => void; onTrace: () => void; onSources: () => void; section:StudioSection;setSection:(value:StudioSection)=>void }) {
  const { state, dispatch, busy, generate, reload, businessContext, saveContext } = useModelingWorkspace(id)
  const [model, setModel] = useState<ModelEntry | null>(null)
  const [contextOpen,setContextOpen]=useState(false)
  const [contextDraft,setContextDraft]=useState('')
  const editContext=()=>{setContextDraft(businessContext);setContextOpen(true)}
  const [view, setView] = useState<'graph' | 'mapping'>('graph')
  const [evidence, setEvidence] = useState(false)
  const [semantic, setSemantic] = useState(false)
  useEffect(() => { void request<ModelEntry>(`modeling/models/${id}`).then(setModel).catch(() => {}) }, [id])
  const checked = state.live?.check?.valid && state.live.check.revision === state.draft?.revision
  return <div className="ontology-space">
    <section className="model-studio reference-studio" aria-label="本体建模工作区">
      <div className="studio-toolbar"><div className="studio-title"><button className="icon-button back-button" aria-label="返回模型列表" title="返回模型列表" onClick={onBack}><Icon name="arrow" size={16}/></button><div><strong className="current-model-name">{model?.name??'本体模型'}</strong><h1>{section === 'materials' ? '建模材料' : section === 'validation' ? '模型校验' : '本体画布'}</h1></div></div><div className="toolbar-actions">
        <span className="studio-version"><span className="version-marker" />{state.draft ? `r${state.draft.revision} · 当前草稿` : '空白模型'}{state.active && <span className="adopted-marker">已采用 r{state.active.version}</span>}</span>
        {section === 'ontology' && <div className="studio-view-toggle" aria-label="本体展示方式"><button aria-pressed={view === 'graph'} onClick={() => setView('graph')}><Icon name="model" size={14} />图谱</button><button disabled={!state.draft} aria-pressed={view === 'mapping'} onClick={() => setView('mapping')}><Icon name="grid" size={14} />映射表</button></div>}
        {section === 'ontology' && <><button className="button secondary" disabled={!state.draft || !!busy} onClick={() => setSection('validation')}>校验模型</button><button className="button primary" disabled={!!busy} onClick={() => setSection('materials')}><Icon name="spark" size={14} />{state.draft ? '材料选择' : '开始建模'}</button></>}
        {section === 'validation' && state.active && <button className="button primary" onClick={onTrace}><Icon name="agent" size={14} />去溯源</button>}
        <button className="icon-button" title="重新读取模型" aria-label="重新读取模型" disabled={!!busy} onClick={reload}><Icon name="refresh" size={15} /></button>
      </div></div>
      {busy && <p className="studio-status" role="status">{busy}</p>}
      {state.error && <p className="message error studio-message" role="alert">{state.error}</p>}
      {state.notice && <p className="message info studio-message" role="status">{state.notice}<button aria-label="关闭提示" className="icon-button" onClick={() => dispatch({ type: 'clear-message' })}><Icon name="close" size={14} /></button></p>}
      <fieldset className="workspace-controls studio-surface" disabled={!!busy}>
        <div className="studio-graph-view" hidden={section !== 'ontology' || view !== 'graph'}>{state.draft ? <OntologyExplorer key={state.live?.runId} state={state} dispatch={dispatch} onEvidence={() => setEvidence(true)} /> : <div className="studio-empty"><span className="empty-model-icon"><Icon name="model" size={34} /></span><h2>在这里构建你的业务本体</h2><p>从已有 DDL、SQL 或文档生成类与关系，在画布上查看并编辑。</p><button className="button primary" onClick={() => setSection('materials')}><Icon name="plus" size={16} />选择建模材料</button></div>}</div>
        {section === 'ontology' && view === 'mapping' && <div className="studio-document-view"><ModelResults state={state} dispatch={dispatch} compact /></div>}
        {section === 'materials' && <div className="studio-document-view studio-materials"><div className="studio-section-intro"><h2>选择模型所需的材料</h2><p>选用数据源接入中已保存的 DDL、SQL 和文档，不在此重复上传。</p><button className="button secondary" onClick={editContext}><Icon name="edit" size={15}/>业务流程说明{businessContext?' · 已填写':''}</button></div><MaterialPicker state={state} dispatch={dispatch} onSources={onSources}/>{businessContext&&<div className="business-context-summary"><strong>业务流程说明</strong><p>{businessContext}</p><button className="text-button" onClick={editContext}>编辑</button></div>}<div className="generation-options"><label className="checkbox-row"><input type="checkbox" checked={semantic} onChange={event => setSemantic(event.target.checked)} />启用语义增强</label><p>将所选材料发送到已配置的模型服务；结构与来源仍由解析器约束。</p></div>{state.draft && <p className="small-note">生成将创建新的草稿版本；原生成记录及采用快照保留。</p>}<div className="dialog-footer"><span>已选 {state.selected.length} 份材料</span><button className="button secondary" onClick={() => setSection('ontology')}>返回画布</button><button className="button primary" disabled={!state.selected.length} onClick={async () => { if (await generate(semantic)) { setSection('ontology'); setView('graph') } }}><Icon name="spark" size={15} />生成本体</button></div></div>}
        {section === 'validation' && <div className="studio-document-view"><div className="studio-section-intro"><h2>检查本体与数据映射</h2><p>静态校验通过后，采用独立版本供溯源问答使用。</p></div><Validation state={state} dispatch={dispatch} /><div className="dialog-footer"><button className="button secondary" onClick={() => setSection('ontology')}>返回画布</button><button className="button primary" disabled={!checked} onClick={() => dispatch({ type: 'adopt' })}><Icon name="check" size={15} />采用当前版本</button></div></div>}
      </fieldset>
      <div className="studio-bottom"><span>{state.draft ? `${state.draft.classes.length} 个类 · ${state.draft.items.length} 个属性 · ${state.draft.relations.length} 条关系` : '尚无本体对象'}</span><span><span className="saved-dot" />{busy ? '正在处理' : state.draft ? `草稿 r${state.draft.revision} · 服务端保存` : '材料生成后保存'}</span></div>
      {contextOpen&&<Dialog title="业务流程说明" onClose={()=>{if(!busy)setContextOpen(false)}}><form className="workbench-form" onSubmit={async event=>{event.preventDefault();if(await saveContext(contextDraft))setContextOpen(false)}}><label>描述业务流程<textarea rows={10} maxLength={10000} value={contextDraft} disabled={!!busy} onChange={event=>setContextDraft(event.target.value)} placeholder="说明业务对象、办理步骤、对象之间的关系及关键字段的含义"/></label><p className="small-note">说明仅属于当前模型，作为下一次生成的原文上下文，不会新增到文档材料库。未启用语义增强时保留为人工核对上下文；开启后仍只接受已有候选与可定位的原文依据，不自动创建新业务概念或源字段。</p>{state.error&&<p className="message error" role="alert">{state.error}</p>}<div className="dialog-footer"><button className="button primary" disabled={!!busy}>{busy||'保存说明'}</button></div></form></Dialog>}
      {evidence && <Dialog title="字段与建模依据" wide onClose={() => setEvidence(false)}><ModelResults state={state} dispatch={dispatch} compact /></Dialog>}
    </section>
  </div>
}
