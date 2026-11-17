import { useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import type { PreviewAction, PreviewState } from './preview'
import OntologyExplorer from './OntologyExplorer'

export default function ModelResults({ state, dispatch }: { state: PreviewState; dispatch: Dispatch<PreviewAction> }) {
  const [selected, setSelected] = useState('cons-no')
  const [view, setView] = useState<'fields' | 'ontology' | 'mapping'>('ontology')
  if (!state.draft) return null
  const items = state.draft.items
  const current = items.find(item => item.id === selected) ?? items[0]
  return <>
    <div className="result-overview"><div className="round-icon mint"><Icon name="check" /></div>
      <div><strong>语义与来源，一起生成</strong><p>{state.draft.classes.length} 个类 · {state.draft.relations.length} 条关系 · {items.filter(item => !item.uncertain && !item.excluded).length} 个可用字段 · {items.filter(item => item.uncertain).length} 个待确认字段</p></div>
      <span className="badge purple">{state.live ? '真实材料分析' : '示例分析结果'}</span>
    </div>
    {state.live && <details className="live-diagnostics"><summary>解析与方法诊断 · {state.live.diagnostics.length} 项</summary><p>{state.live.stats.tables} 张表 · {state.live.stats.columns} 个字段 · {state.live.stats.queries_parsed} 条查询已解析 · {state.live.method}</p>{state.live.diagnostics.map((d,i) => <p key={i}><code>{d.code}</code> {d.message}</p>)}</details>}
    <div className="result-toolbar"><h2>本体与映射</h2>
      <div className="segmented" aria-label="结果视图">
        {([['ontology', '完整本体'], ['fields', '字段与证据'], ['mapping', '数据映射']] as const).map(([id, label]) =>
          <button key={id} onClick={() => setView(id)} aria-pressed={view === id}>{label}</button>)}
      </div>
    </div>
    {view === 'fields' && <div className="candidate-workspace">
      <div className="candidate-list" aria-label="字段候选">
        {items.map(item => <button key={item.id} onClick={() => setSelected(item.id)} aria-pressed={current.id === item.id}>
          <span className={`candidate-icon ${item.uncertain ? 'amber' : item.kind === 'calculated' ? 'purple' : 'blue'}`}><Icon name={item.uncertain ? 'info' : item.kind === 'calculated' ? 'code' : 'model'} /></span>
          <span><strong>{item.name}</strong><small>{item.concept}</small></span>
          <span className={`candidate-state ${item.uncertain ? 'warning-text' : item.excluded ? 'subtle' : 'good-text'}`}>
            {item.uncertain ? '待确认' : item.excluded ? '已排除' : '有依据'}</span>
        </button>)}
      </div>
      <article className="candidate-detail">
        <div className="section-heading"><div><span className="eyebrow">{current.concept} / {current.kind === 'calculated' ? '计算指标' : '业务属性'}</span>
          <h3>{current.name}</h3></div><span className={`badge ${current.uncertain ? 'amber' : 'mint'}`}>{current.uncertain ? '需补充上下文' : '多材料支持'}</span></div>
        <p>{current.description}</p>
        {current.aliases.length > 0 && <p className="alias-label">同义叫法 {current.aliases.map(alias => <span className="tag" key={alias}>{alias}</span>)}</p>}
        <div className="source-binding"><span>{current.uncertain ? '存在两个物理来源' : '来源字段'}</span>
          {current.sources.map(source => <code key={source}>{source}</code>)}
          {current.expression && <div className="formula"><b>计算口径</b><code>{current.expression}</code><p>{current.scope}</p></div>}
        </div>
        <h4 className="evidence-heading"><Icon name="file" size={17} />为什么这样建模<span>{current.evidence.length} 处依据</span></h4>
        <div className="evidence-list">{current.evidence.map((evidence, index) => <div key={index}>
          <div><span className="evidence-number">{index + 1}</span><strong>{evidence.label}</strong><small>{state.materials.find(item => item.id === evidence.materialId)?.name}</small></div>
          <blockquote>{evidence.quote}</blockquote>
        </div>)}</div>
        {current.uncertain ? <div className="message amber"><Icon name="info" size={18} /><span>保留为待确认项，暂不进入溯源版本。补充页面信息后再确定，其他字段可以继续使用。</span></div> :
          <div className="candidate-actions"><span>{current.excluded ? '此字段不会进入采用版本。' : '此字段将进入可用模型。'}</span>
            <button className="text-button" onClick={() => dispatch({ type: 'exclude', id: current.id, excluded: !current.excluded })}>
              {current.excluded ? '重新纳入' : '暂不采用此字段'}</button></div>}
      </article>
    </div>}
    <div hidden={view !== 'ontology'}><OntologyExplorer state={state} dispatch={dispatch} /></div>
    {view === 'mapping' && <section className="mapping-view">
      <p className="mapping-intro">本体属性与源列绑定；计算指标保留依赖列和表达式。</p>
      <div className="table-scroll"><table><thead><tr><th>业务对象 / 属性</th><th>物理来源</th><th>映射方式</th><th>采用范围</th></tr></thead>
        <tbody>{items.map(item => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.concept}</small></td>
          <td>{item.sources.map(source => <code key={source}>{source}</code>)}</td><td>{item.kind === 'calculated' ? '派生依赖' : '属性 → 物理列'}</td>
          <td><span className={`badge ${item.uncertain ? 'amber' : item.excluded ? '' : 'mint'}`}>{item.uncertain ? '待确认' : item.excluded ? '已排除' : '可纳入'}</span></td></tr>)}</tbody>
      </table></div><p className="small-note">{state.live ? '校验时调用 OntoWing，采用后导出 OWL / R2RML；计算字段保留依赖清单，映射实跑尚未执行。' : '此处为示例交互，未执行真实校验。'}</p>
    </section>}
    <details className="analysis-details"><summary><Icon name="clock" size={17} />查看分析过程与建模方法<span>{state.live ? '结构分析方法' : '示例过程'}</span></summary>
      <ol>{[
        ['读取材料', '按 DDL、SQL、文档分别处理，保留原始来源。'],
        ['发现语义', '从字段注释、投影别名与计算表达式形成候选；查询频率只影响优先级。'],
        ['对齐与消歧', '合并有证据的同义叫法，区分业务标识和技术主键，保留电话字段歧义。'],
        ['建立本体与映射', '业务属性绑定物理列；计算字段携带表达式、条件与粒度。'],
      ].map(([title, text]) => <li key={title}><Icon name="check" size={16} /><div><strong>{title}</strong><p>{text}</p></div></li>)}</ol>
    </details>
  </>
}
