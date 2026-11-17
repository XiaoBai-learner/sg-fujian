import { useEffect, useState, type FormEvent } from 'react'
import Icon from '../../shared/Icon'
import { cardinalities, datatypes, type OntologySelection } from './OntologyGraph'
import type { Candidate, OntologyDraft, OntologyRelation, PreviewAction, Material } from './preview'

type FormValues = {
  name: string; description: string; aliases: string; parentId: string; conceptId: string; datatype: Candidate['datatype']; unit: string
  sourceId: string; targetId: string; cardinality: OntologyRelation['cardinality']; symmetric: boolean; transitive: boolean; functional: boolean
}
export default function OntologyInspector({ draft, selection, materials, onSave, onDirty }: {
  draft: OntologyDraft; selection: OntologySelection; materials: Material[]
  onSave: (action: PreviewAction) => string | null; onDirty: (dirty: boolean) => void
}) {
  const cls = selection.kind === 'class' ? draft.classes.find(item => item.id === selection.id) : undefined
  const property = selection.kind === 'property' ? draft.items.find(item => item.id === selection.id) : undefined
  const relation = selection.kind === 'relation' ? draft.relations.find(item => item.id === selection.id) : undefined
  const item = cls ?? property ?? relation
  const initial: FormValues = {
    name: item?.name ?? '', description: item?.description ?? '', aliases: (cls?.aliases ?? property?.aliases ?? []).join('、'),
    parentId: cls?.parentId ?? '', conceptId: property?.conceptId ?? '', datatype: property?.datatype ?? 'string', unit: property?.unit ?? '',
    sourceId: relation?.sourceId ?? '', targetId: relation?.targetId ?? '', cardinality: relation?.cardinality ?? 'unknown',
    symmetric: relation?.symmetric ?? false, transitive: relation?.transitive ?? false, functional: relation?.functional ?? false,
  }
  const [form, setForm] = useState(initial)
  const [error, setError] = useState('')
  const initialKey = JSON.stringify(initial)
  // Unrelated draft edits must not reset the form; sync only its own saved fields.
  useEffect(() => { setForm(JSON.parse(initialKey)); setError('') }, [initialKey])
  const dirty = JSON.stringify(form) !== initialKey
  useEffect(() => { onDirty(dirty) }, [dirty, onDirty])
  if (!item) return <div className="ontology-inspector"><p>请选择一个类、属性或关系。</p></div>
  const change = (values: Partial<FormValues>) => { setForm(current => ({ ...current, ...values })); setError('') }
  const aliases = () => [...new Set(form.aliases.split(/[、,，;\n]/).map(text => text.trim()).filter(Boolean))]
  const save = (event: FormEvent) => {
    event.preventDefault()
    let action: PreviewAction
    if (cls) action = { type: 'edit-class', value: { ...cls, name: form.name, description: form.description, aliases: aliases(), parentId: form.parentId || null } }
    else if (property) action = { type: 'edit-property', value: { ...property, name: form.name, description: form.description, aliases: aliases(),
      conceptId: form.conceptId || null, datatype: form.datatype, unit: form.unit } }
    else action = { type: 'edit-relation', value: { ...relation!, name: form.name, description: form.description, sourceId: form.sourceId,
      targetId: form.targetId, cardinality: form.cardinality, symmetric: form.symmetric, transitive: form.transitive, functional: form.functional } }
    const issue = onSave(action)
    if (issue) setError(issue)
  }
  return <aside className="ontology-inspector" aria-label="本体详情编辑">
    <div className="inspector-title"><span className={`tiny-icon ${relation ? 'blue' : property ? 'mint' : 'purple'}`}><Icon name={relation ? 'arrow' : property ? 'code' : 'model'} size={16} /></span>
      <div><span>{cls ? '类 CLASS' : property ? '属性 PROPERTY' : '关系 RELATION'}</span><h3>{item.name}</h3></div>
      {dirty && <span className="badge amber">未保存</span>}
    </div>
    <form className="ontology-form" onSubmit={save}>
      <label htmlFor="ontology-name">名称</label>
      <input id="ontology-name" required maxLength={160} value={form.name} onChange={event => change({ name: event.target.value })} />
      <label htmlFor="ontology-description">业务说明</label>
      <textarea id="ontology-description" rows={3} maxLength={2000} value={form.description} onChange={event => change({ description: event.target.value })} />
      {!relation && <>
        <label htmlFor="ontology-aliases">同义叫法</label><input id="ontology-aliases" maxLength={1000} value={form.aliases}
          placeholder="用顿号或逗号分隔" onChange={event => change({ aliases: event.target.value })} />
      </>}
      {cls && <>
        <label htmlFor="ontology-parent">父类</label><select id="ontology-parent" value={form.parentId} onChange={event => change({ parentId: event.target.value })}>
          <option value="">无父类（顶层类）</option>{draft.classes.filter(item => item.id !== cls.id).map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        <div className="inspector-associated"><h4>属性与关系</h4><p>{draft.items.filter(item => item.conceptId === cls.id).map(item => item.name).join('、') || '暂无归属已确定的属性'}</p>
          <p>{draft.relations.filter(item => item.sourceId === cls.id || item.targetId === cls.id).map(item => item.name).join('、') || '暂无关系'}</p></div>
      </>}
      {property && <>
        <label htmlFor="ontology-owner">所属类</label><select id="ontology-owner" value={form.conceptId} onChange={event => change({ conceptId: event.target.value })}>
          {property.uncertain && <option value="">待确认</option>}{draft.classes.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        <div className="form-columns"><div><label htmlFor="ontology-datatype">数据类型</label><select id="ontology-datatype" value={form.datatype} onChange={event => change({ datatype: event.target.value as Candidate['datatype'] })}>
          {Object.entries(datatypes).map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></div>
          <div><label htmlFor="ontology-unit">单位</label><input id="ontology-unit" maxLength={40} value={form.unit} onChange={event => change({ unit: event.target.value })} placeholder="如：元" /></div></div>
        <div className="inspector-associated"><h4>来源映射 · 只读</h4>{property.sources.map(source => <code key={source}>{source}</code>)}
          {property.expression && <><h4>计算口径 · 只读</h4><code>{property.expression}</code><p>{property.scope}</p></>}
          <p>语义编辑不会改写原始证据和物理映射；类型与映射一致性待后端校验。</p></div>
      </>}
      {relation && <>
        <div className="relation-direction"><span>关系方向：起点 → 终点</span><button type="button" className="text-button"
          onClick={() => change({ sourceId: form.targetId, targetId: form.sourceId,
            cardinality: form.cardinality === 'one-to-many' ? 'many-to-one' : form.cardinality === 'many-to-one' ? 'one-to-many' : form.cardinality })}>反转方向<Icon name="arrow" size={14} /></button></div>
        <label htmlFor="ontology-source">起点类（Domain）</label><select id="ontology-source" value={form.sourceId} onChange={event => change({ sourceId: event.target.value })}>
          {draft.classes.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        <label htmlFor="ontology-target">终点类（Range）</label><select id="ontology-target" value={form.targetId} onChange={event => change({ targetId: event.target.value })}>
          {draft.classes.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        <label htmlFor="ontology-cardinality">起点到终点的关系基数</label><select id="ontology-cardinality" value={form.cardinality} onChange={event => change({ cardinality: event.target.value as OntologyRelation['cardinality'] })}>
          {Object.entries(cardinalities).map(([value, label]) => <option key={value} value={value}>{label}{value === 'unknown' ? '' : value === 'one-to-one' ? ' · 一对一' : value === 'one-to-many' ? ' · 一对多' : value === 'many-to-one' ? ' · 多对一' : ' · 多对多'}</option>)}</select>
        <fieldset className="relation-characteristics"><legend>关系特性</legend>
          <label><input type="checkbox" checked={form.symmetric} onChange={event => change({ symmetric: event.target.checked })} />对称关系</label>
          <label><input type="checkbox" checked={form.transitive} onChange={event => change({ transitive: event.target.checked })} />传递关系</label>
          <label><input type="checkbox" checked={form.functional} onChange={event => change({ functional: event.target.checked })} />至多一个终点</label>
        </fieldset>
        <p className="inspector-help">基数和关系特性是语义声明，不会由 JOIN 次数自动确认。</p>
      </>}
      {(property?.uncertain || relation?.uncertain) && <p className="message amber">来源尚有歧义。编辑不会自动确认该候选，仍不纳入采用版本。</p>}
      {error && <p className="message error" role="alert">{error}</p>}
      <div className="ontology-save"><button type="button" className="button secondary" disabled={!dirty} onClick={() => { setForm(initial); setError('') }}>取消修改</button>
        <button className="button primary" type="submit" disabled={!dirty}><Icon name="check" size={16} />保存到草稿</button></div>
    </form>
    <details className="inspector-provenance" open><summary>来源依据 <span>{item.evidence.length} 处</span></summary>
      {item.edited && <p className="edit-provenance"><Icon name="info" size={14} />已人工编辑。以下是原始生成依据，不代表对修改的验证。</p>}
      {item.evidence.map((evidence, index) => <div key={index}><strong>{evidence.label}</strong><small>{materials.find(material => material.id === evidence.materialId)?.name}</small><blockquote>{evidence.quote}</blockquote></div>)}
    </details>
    <details className="inspector-provenance"><summary>稳定标识</summary><code>{item.id}</code><p>修改显示名称不改变此标识与引用。</p></details>
  </aside>
}
