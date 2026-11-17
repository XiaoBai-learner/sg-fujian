import { useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import { MaterialInput } from './MaterialInput'
import ModelResults from './ModelResults'
import Validation from './Validation'
import type { PreviewAction, PreviewState } from './preview'

type Step = 'materials' | 'results' | 'validation'
export default function ModelingPage({ state, dispatch, onTrace, onGenerate, onReload }: {
  state: PreviewState; dispatch: Dispatch<PreviewAction>; onTrace: () => void; onGenerate: (semantic:boolean) => Promise<void>; onReload: () => void
}) {
  const [step, setStep] = useState<Step>('materials')
  const [semantic, setSemantic] = useState(false)
  const current = !state.draft ? 'materials' : step
  const example = state.selected.length > 0 && state.materials.filter(m => state.selected.includes(m.id)).every(m => m.origin === 'example')
  const generate = async () => { await onGenerate(semantic); setStep('results') }
  const usable = state.draft?.items.filter(item => !item.uncertain && !item.excluded).length ?? 0
  const checked = state.live ? state.live.check?.valid && state.live.check.revision === state.draft?.revision : state.draft && usable > 0 && state.validation?.revision === state.draft.revision && state.validation.cases.every(item => item.passed || item.skipped)
  return <section className="modeling-page">
    <div className="page-heading"><div><div className="eyebrow"><span className="tiny-icon purple"><Icon name="spark" size={14} /></span>智能本体构建</div>
      <h1>让原始材料，成为溯源的起点</h1><p>传入结构、SQL 与业务资料，生成有据可查的本体和映射。</p></div>
      <div className={`model-version ${state.active ? 'is-active' : ''}`}><Icon name="model" size={18} /><span>{state.active ? `${state.active.snapshotId ? '模型' : '示例模型'} r${state.active.version} 已采用` : '还没有采用模型'}</span></div>
    </div>
    <div className="workflow-steps" aria-label="智能建模流程">
      {([
        ['materials', '01', '准备材料', '原始输入，统一选用'],
        ['results', '02', '本体与证据', '生成、对齐与消歧'],
        ['validation', '03', '验证并使用', '检查后用于字段溯源'],
      ] as const).map(([id, number, title, subtitle]) => <button key={id} disabled={id !== 'materials' && !state.draft}
        onClick={() => { setStep(id); dispatch({ type: 'clear-message' }) }} aria-current={current === id ? 'step' : undefined}>
        <span className="step-number">{(id === 'materials' && state.draft) || (id === 'results' && checked) ? <Icon name="check" size={16} /> : number}</span>
        <span><strong>{title}</strong><small>{subtitle}</small></span><Icon name="chevron" size={16} /></button>)}
    </div>
    {state.error && <p className="message error" role="alert"><Icon name="info" size={18} />{state.error}</p>}
    {state.notice && <p className="message info" role="status"><Icon name="info" size={17} />{state.notice}</p>}
    <div className="modeling-surface">
      {current === 'materials' && <>
        <div className="surface-heading"><div><h2>从你已有的材料开始</h2><p>无需先写业务模型，DDL 和热点 SQL 也可以作为建模输入。</p></div><span className="badge blue"><Icon name="folder" size={14} />统一材料库</span></div>
        <MaterialInput state={state} dispatch={dispatch} />
        <div className="semantic-options"><label><input type="checkbox" checked={semantic} onChange={event => setSemantic(event.target.checked)} />启用模型语义增强</label><p>开启后，所选材料会发送到部署配置的模型服务；只接受已有候选 ID 和可定位原文。未开启时仍执行真实 DDL / SQL 结构与使用证据分析。</p><button className="text-button" onClick={onReload}>重新读取服务端记录</button></div>
        <div className="method-strip"><span><Icon name="source" size={17} />结构约束</span><i>+</i><span><Icon name="code" size={17} />SQL 使用证据</span><i>+</i><span><Icon name="file" size={17} />业务语义</span><Icon name="arrow" size={18} /><strong>本体与来源映射</strong></div>
      </>}
      {state.draft && <div hidden={current !== 'results'}><ModelResults state={state} dispatch={dispatch} /></div>}
      {current === 'validation' && <Validation state={state} dispatch={dispatch} />}
      <footer className="workflow-footer">
        <div><span className="footer-indicator" /><span>{current === 'materials' ? `已选 ${state.selected.length} 份材料` : `${usable} 个字段可纳入 · ${state.draft?.items.filter(i => i.uncertain).length ?? 0} 个字段保留待确认`}</span>
          <small>{current === 'materials' ? '结构与文档保留各自来源' : '草稿不会改变当前溯源版本'}</small></div>
        {current === 'materials' && <button className="button primary" disabled={!state.selected.length} onClick={() => void generate()}><Icon name="spark" size={17} />{example ? '生成本体 · 示例' : '生成本体'}<Icon name="arrow" size={17} /></button>}
        {current === 'results' && <button className="button primary" onClick={() => setStep('validation')}>校验模型与映射<Icon name="arrow" size={17} /></button>}
        {current === 'validation' && <div className="footer-actions">
          {state.active && <button className="button secondary" onClick={onTrace}>使用已采用版本<Icon name="arrow" size={16} /></button>}
          <button className="button primary" disabled={!checked} onClick={() => dispatch({ type: 'adopt' })}><Icon name="check" size={17} />{state.live ? '采用模型快照' : '采用示例模型'}</button>
        </div>}
      </footer>
    </div>
    <p className="page-footnote"><Icon name="shield" size={15} />构建方法以真实结构与 SQL 证据为依据。静态校验不代表业务语义或实际映射运行已验证。</p>
  </section>
}
