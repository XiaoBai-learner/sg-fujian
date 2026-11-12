import { useEffect, useState } from 'react'
import { AsyncState } from '../components/AsyncState'
import StatusBadge from '../components/StatusBadge'
import type { KnowledgeDraft } from '../domain/types'
import { getKnowledgeDraft } from '../services/mockService'

const concepts = [
  { id: 'consumer', label: '用电客户', meta: '12 个属性 · 4 条关系' },
  { id: 'receivable', label: '应收电费', meta: '9 个属性 · 2 条关系' },
  { id: 'workorder', label: '95598 工单', meta: '15 个属性 · 3 条关系' },
  { id: 'metering', label: '计量点', meta: '10 个属性 · 5 条关系' },
  { id: 'derived', label: '派生业务分类', meta: '7 条规则' },
]

export default function KnowledgeModelPage() {
  const [draft, setDraft] = useState<KnowledgeDraft>()
  const [selected, setSelected] = useState('consumer')
  const [tab, setTab] = useState<'concept' | 'attribute' | 'relation' | 'rule'>('attribute')
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => { setLoading(true); getKnowledgeDraft().then(setDraft).catch(e => setError(e instanceof Error ? e.message : '草稿读取失败')).finally(() => setLoading(false)) }
  useEffect(load, [])
  return <AsyncState loading={loading} error={error} onRetry={load}>{draft && <><div className="page-head"><div><p className="page-kicker">KNOWLEDGE WORKSPACE / SEMANTIC MODEL</p><h1>语义模型</h1><p>人工修订记录在草稿中，只有验证、审核和发布后才影响业务查询。</p></div><div className="page-actions"><StatusBadge label={`草稿 R${draft.revision}`} tone="amber" /><button className="btn" type="button" onClick={() => setSaved(true)}>保存草稿修订</button><button className="btn primary" type="button" onClick={() => window.location.assign('/knowledge/validation')}>前往验证</button></div></div>
    <div className="notice"><span><strong>{draft.title}</strong> · 最近修改 {draft.updatedAt} · {draft.updatedBy}。当前页面编辑仅修改草稿，不会影响线上版本。</span>{saved && <StatusBadge label="已保存" tone="green" />}</div>
    <div className="split section-gap"><section className="panel"><div className="panel-head"><div><h2>模型目录</h2><p>按概念、派生分类和关系查看当前草稿。</p></div><StatusBadge label={`${draft.concepts} 个对象`} tone="blue" /></div><div className="panel-body tree">{concepts.map(concept => <button className={`tree-row${selected === concept.id ? ' selected' : ''}`} type="button" key={concept.id} onClick={() => setSelected(concept.id)}><span className="tree-mark">{concept.id === 'derived' ? 'R' : 'C'}</span><span>{concept.label}<small className="muted-cell">{concept.meta}</small></span><span>›</span></button>)}</div></section><section className="panel"><div className="panel-head"><div><h2>模型工作区 · {concepts.find(item => item.id === selected)?.label}</h2><p>选择编辑分区查看草稿对象和证据。</p></div></div><div className="panel-body"><div className="tabs">{[['concept', '概念'], ['attribute', '属性'], ['relation', '关系'], ['rule', '规则']].map(([id, label]) => <button className={`tab${tab === id ? ' active' : ''}`} type="button" key={id} onClick={() => setTab(id as typeof tab)}>{label}</button>)}</div>{tab === 'attribute' && <AttributeEditor draft={draft} />}{tab === 'concept' && <div className="notice section-gap"><span><strong>用电客户</strong><br />供电营销业务中的客户主体，当前有 12 个属性和 4 条关系。定义依据来自业务说明和客户表注释。</span></div>}{tab === 'relation' && <div className="notice section-gap"><span><strong>归属供电单位</strong><br /><code>yx186.C_CONS.ORG_NO → yx186.O_ORG.ORG_NO</code><br />关系证据：源系统键约定 + 任务 SQL JOIN。</span></div>}{tab === 'rule' && <div className="notice section-gap"><span><strong>重点关注客户</strong><br />欠费客户 ∧ 投诉客户。事实规则与建议规则分开发布，阈值需要业务审核。</span></div>}</div></section></div>
    <section className="panel section-gap"><div className="panel-head"><div><h2>草稿变更</h2><p>生成候选版本前先处理未验证和冲突项。</p></div><StatusBadge label={`${draft.pendingChanges.length} 项`} tone="amber" /></div><div className="panel-body grid">{draft.pendingChanges.map(change => <div className="notice" key={change.id}><StatusBadge label={change.status === 'accepted' ? '已确认' : change.status === 'conflict' ? '冲突' : '未验证'} tone={change.status === 'accepted' ? 'green' : change.status === 'conflict' ? 'red' : 'amber'} /><span><strong>{change.label}</strong><br />{change.detail}</span></div>)}</div></section>
  </>}</AsyncState>
}

function AttributeEditor({ draft }: { draft: KnowledgeDraft }) {
  return <div className="section-gap"><div className="notice ok"><span><strong>{draft.selectedAttribute.label}</strong><br />{draft.selectedAttribute.definition}</span><StatusBadge label="有映射" tone="green" /></div><dl className="detail-kv"><dt>接受叫法</dt><dd>{draft.selectedAttribute.aliases.map(alias => <code key={alias}>{alias}</code>)}</dd><dt>物理映射</dt><dd><code>{draft.selectedAttribute.mapping}</code></dd><dt>页面使用</dt><dd>{draft.selectedAttribute.usage}</dd><dt>证据</dt><dd>{draft.selectedAttribute.evidence}</dd></dl><div className="form-field section-gap"><label htmlFor="alias-input">增加叫法（草稿）</label><input id="alias-input" placeholder="输入业务人员在页面上使用的叫法" /></div></div>
}
