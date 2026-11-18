import type { Dispatch } from 'react'
import type { WorkspaceAction, WorkspaceState } from './state'

export default function Validation({ state, dispatch }: { state: WorkspaceState; dispatch: Dispatch<WorkspaceAction> }) {
  if (!state.live) return <p className="message info">请先生成服务端草稿。</p>
  return <section className="live-check"><div className="section-heading"><h2>真实模型与映射校验</h2><button className="button secondary" onClick={() => dispatch({type:'validate'})}>运行 OntoWing 校验</button></div>
    <p>使用本轮真实结构快照检查对象、字段类型、实体键和关联映射，并编译 OWL / R2RML。不会执行上传的业务 SQL。</p>
    {state.live.check ? <><p className={`message ${state.live.check.valid ? 'info' : 'error'}`} role="status">{state.live.check.valid ? '静态校验通过，可采用为模型快照。' : '校验存在问题，请修改草稿或补充材料。'} · r{state.live.check.revision}</p>
      <ul>{state.live.check.problems.map((p,i) => <li key={i}>{p.message}</li>)}{Object.values(state.live.check.reports).flatMap(r => r.diagnostics).map((d,i) => <li key={`d${i}`}>{d.severity}：{d.message}</li>)}</ul>
      <p>导出损失：{state.live.check.losses.join('、') || '无'}</p></> : <p className="message info">尚未运行，或草稿修改后校验已失效。</p>}
    <p className="small-note">本轮仅验证结构与导出一致性；Morph-KGC 实跑、业务口径 SQL 对账和独立效果集尚未执行，不能将静态通过称为准确率。</p>
    {state.active?.snapshotId && <div className="footer-actions"><a className="button secondary" href={`/api/v1/modeling/snapshots/${state.active.snapshotId}/ontology.ttl`}>下载已采用 OWL</a><a className="button secondary" href={`/api/v1/modeling/snapshots/${state.active.snapshotId}/mapping.ttl`}>下载已采用 R2RML</a></div>}
  </section>
}
