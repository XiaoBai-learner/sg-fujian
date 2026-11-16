import { useEffect, useState } from 'react'
import { ModelRecognitionStep } from '@wing/product/modeling-editors/recognition-step'
import { StructuredModelingEditor } from '@wing/product/modeling-editors'
import { setETLCatalogSession } from '@wing/product/etl-catalog'
import type { Editors, Page, Workspace } from '../domain/types'
import { activateModel, checkModel } from '../services/workspace'
import { MODEL_ID } from '../services/wingCatalog'
import Icon from '../components/Icon'

type Tab = 'entities' | 'relations' | 'pipeline' | 'rules'
const tabs: [Tab, string][] = [['entities', '对象与属性'], ['relations', '关系图'], ['pipeline', 'R2RML 数据映射'], ['rules', '业务规则']]

export default function ModelingPage({ state, onEdit, onChange, onNavigate }: {
  state: Workspace; onEdit: (editors: Editors) => void; onChange: (value: Workspace) => void; onNavigate: (page: Page) => void
}) {
  const [tab, setTab] = useState<Tab>('entities')
  const [report, setReport] = useState<string[] | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => { setETLCatalogSession({ subject: 'workspace', organization: 'sgtrace', roles: [] }); return () => setETLCatalogSession(null) }, [])
  const update = (key: keyof Editors, value: Record<string, unknown>) => {
    onEdit({ ...state.editors, [key]: value } as Editors)
    setReport(null); setMessage('')
  }
  const apply = () => {
    try { onChange(activateModel(state)); setMessage('当前本体与映射已用于溯源。'); setReport([]) }
    catch (error) { setReport([error instanceof Error ? error.message : '请先检查模型。']) }
  }
  return <>
    <div className="module-heading"><div><span className="eyeline">02 / ONTOWING</span><h1>把数据变成业务本体</h1><p>定义对象、属性与关系，建立到源表字段的 R2RML 映射。</p></div><div className="compact-actions"><button className="action" onClick={() => { setReport(checkModel(state.editors)); setMessage('') }}>检查模型</button><button className="action primary" onClick={apply}>用于字段溯源<Icon name="arrow" /></button></div></div>
    <div className="model-context"><span className="ontowing-word">OntoWing</span><span>营销域本体</span><span className="context-divider" /><span>{state.editors.model.concepts.length} 个对象</span><span>{state.editors.model.attributes.length} 个属性</span><span>{state.editors.pipeline.bindings.length} 个表绑定</span><span className="context-end status-label"><i />{state.revision === state.active.revision ? `v${state.active.revision} 正在使用` : '有新修改，尚未用于溯源'}</span></div>
    <div className="model-tabs" role="tablist" aria-label="本体编辑">{tabs.map(([id, title]) => <button role="tab" aria-selected={tab === id} key={id} onClick={() => setTab(id)}>{title}</button>)}</div>
    {message && <p className="success-note" role="status"><Icon name="check" />{message}<button className="text-action" onClick={() => onNavigate('agent')}>去提问 →</button></p>}
    {report !== null && !message && <div className={report.length ? 'error-note' : 'inline-note'} role="status">{report.length ? report.map((issue, i) => <p key={i}>{issue}</p>) : '本地基础检查通过。正式 OntoWing 校验与 TTL 导出在后端接入后执行。'}</div>}
    <section className="wing-editor" aria-label="OntoWing 本体工作区">
      {(tab === 'entities' || tab === 'relations') && <ModelRecognitionStep editor={state.editors.model as unknown as Record<string, unknown>} mode={tab} revision={state.active.revision} disabled={false} onChange={value => update('model', value)} onRelationSelect={() => setTab('relations')} />}
      {(tab === 'pipeline' || tab === 'rules') && <StructuredModelingEditor kind={tab} content={state.editors[tab] as unknown as Record<string, unknown>} model={state.editors.model as unknown as Record<string, unknown>} modelId={MODEL_ID} modelName="营销域本体" disabled={false} onChange={value => update(tab, value)} />}
    </section>
    <div className="model-footnote"><span>修改自动保存在本机浏览器。点击“用于字段溯源”后，智能体采用新的本体与映射。</span><span>原型使用本地基础检查与模拟检索。</span></div>
  </>
}
