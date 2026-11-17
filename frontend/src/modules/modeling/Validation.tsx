import { useState, type Dispatch } from 'react'
import Icon from '../../shared/Icon'
import { tracePreview, type PreviewAction, type PreviewState } from './preview'

export default function Validation({ state, dispatch }: { state: PreviewState; dispatch: Dispatch<PreviewAction> }) {
  const [field, setField] = useState('')
  const [tested, setTested] = useState('')
  const result = state.draft && tested ? tracePreview({ version: 0, ...state.draft }, tested) : null
  const cases = state.validation?.cases
  if (state.live) return <section className="live-check"><div className="section-heading"><h2>真实模型与映射校验</h2><button className="button secondary" onClick={() => dispatch({type:'validate'})}>运行 OntoWing 校验</button></div>
    <p>使用本轮真实结构快照检查对象、字段类型、实体键和关联映射，并编译 OWL / R2RML。不会执行上传的业务 SQL。</p>
    {state.live.check ? <><p className={`message ${state.live.check.valid ? 'info' : 'error'}`} role="status">{state.live.check.valid ? '静态校验通过，可采用为模型快照。' : '校验存在问题，请修改草稿或补充材料。'} · r{state.live.check.revision}</p>
      <ul>{state.live.check.problems.map((p,i) => <li key={i}>{p.message}</li>)}{Object.values(state.live.check.reports).flatMap(r => r.diagnostics).map((d,i) => <li key={`d${i}`}>{d.severity}：{d.message}</li>)}</ul>
      <p>导出损失：{state.live.check.losses.join('、') || '无'}</p></> : <p className="message info">尚未运行，或草稿修改后校验已失效。</p>}
    <p className="small-note">本轮仅验证结构与导出一致性；Morph-KGC 实跑、业务口径 SQL 对账和独立效果集尚未执行，不能将静态通过称为准确率。</p>
    {state.active?.snapshotId && <div className="footer-actions"><a className="button secondary" href={`/api/v1/modeling/snapshots/${state.active.snapshotId}/ontology.ttl`}>下载已采用 OWL</a><a className="button secondary" href={`/api/v1/modeling/snapshots/${state.active.snapshotId}/mapping.ttl`}>下载已采用 R2RML</a></div>}
  </section>
  return <div className="validation-layout">
    <section className="validation-main">
      <div className="section-heading"><div><span className="eyebrow">用答案，检查建模结果</span><h2>字段溯源验证</h2></div>
        <button className="button secondary" onClick={() => dispatch({ type: 'validate' })}><Icon name="shield" size={17} />运行示例检查</button></div>
      <p>用独立手工答案核对当前草稿的来源列，包括同义字段、计算依赖和歧义拒答。</p>
      {cases ? <>
        <div className={`validation-summary ${cases.some(item => !item.passed && !item.skipped) ? 'warning' : ''}`} role="status"><Icon name="shield" size={22} />
          <div><strong>{cases.filter(item => item.passed).length} / {cases.filter(item => !item.skipped).length} 项来源集合一致</strong>
            <span>合成样例自检 · {cases.filter(item => item.skipped).length} 项已排除 · 不作为识别准确率</span></div></div>
        <div className="table-scroll"><table className="validation-table"><thead><tr><th>检验字段</th><th>本次结果</th><th>对照结果</th></tr></thead><tbody>
          {cases.map(item => <tr key={item.field}><td><strong>{item.field}</strong><small>{item.note}</small></td>
            <td>{item.actual.length ? item.actual.map(source => <code key={source}>{source}</code>) : <span className={item.skipped ? 'subtle' : 'warning-text'}>{item.skipped ? '已排除，不参与当前检查' : '暂不采用，等待补证'}</span>}</td>
            <td><span className={`check-label ${item.skipped ? 'subtle' : item.passed ? 'good-text' : 'warning-text'}`}><Icon name={item.passed ? 'check' : 'info'} size={16} />{item.skipped ? '已跳过' : item.passed ? '符合预期' : '不一致'}</span></td></tr>)}
        </tbody></table></div>
      </> : <div className="validation-empty"><span className="round-icon mint"><Icon name="shield" size={26} /></span>
        <h3>生成了本体，还要看能否找到正确字段</h3><p>运行 5 个合成样例检查，结果与当前草稿绑定。修改草稿后需要重新检查。</p></div>}
      <form className="quick-test" onSubmit={event => { event.preventDefault(); setTested(field.trim()) }}>
        <label htmlFor="test-field">也可以用一个字段试试看</label><div><input id="test-field" value={field} onChange={event => setField(event.target.value)} placeholder="例如：客户名称、欠费金额" maxLength={100} />
          <button className="button secondary" disabled={!field.trim()} type="submit">试一试<Icon name="arrow" size={16} /></button></div>
        {result && <div className="trial-result" role="status"><strong>{tested}</strong>{result.sources.length ? result.sources.map(source => <code key={source}>{source}</code>) :
          <span>当前可用草稿没有明确来源，请补充材料或业务上下文。</span>}{result.item?.scope && <small>{result.item.scope}</small>}</div>}
      </form>
    </section>
    <aside className="validation-aside">
      <h3>正确性来自哪里</h3>
      <div><span className="round-icon mint"><Icon name="check" size={18} /></span><h4>示例答案核对</h4><p>来源列集合与独立手工答案比对。当前可运行。</p><span className={`badge ${cases ? 'mint' : ''}`}>{cases ? '已运行' : '待运行'}</span></div>
      <div><span className="round-icon blue"><Icon name="model" size={18} /></span><h4>模型与映射执行</h4><p>OntoWing 校验、R2RML 实跑及 SQL 对账，由后端接入。</p><span className="badge">尚未执行</span></div>
      <div><span className="round-icon purple"><Icon name="file" size={18} /></span><h4>真实效果评测</h4><p>使用留出问题、专家标注和外部数据集验证构建方法。</p><span className="badge">尚未运行</span></div>
    </aside>
  </div>
}
