import { useId, useLayoutEffect, useRef, useState } from 'react'
import Icon from '../../shared/Icon'
import type { OntologyDraft } from './state'
import { layoutOntology } from './ontology-layout'

export type OntologySelection = { kind: 'class' | 'property' | 'relation'; id: string }
const label = (text: string, max = 14) => text.length > max ? `${text.slice(0, max)}…` : text
export const cardinalities = { unknown: '未确定', 'one-to-one': '1 : 1', 'one-to-many': '1 : N', 'many-to-one': 'N : 1', 'many-to-many': 'N : M' }
export const datatypes = { string: '文本', integer: '整数', decimal: '小数', boolean: '是 / 否', date: '日期', datetime: '日期时间' }

export default function OntologyGraph({ draft, selected, onSelect }: {
  draft: OntologyDraft; selected: OntologySelection; onSelect: (selection: OntologySelection) => void
}) {
  const viewport = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [width, setWidth] = useState(700)
  const marker = useId().replace(/:/g, '')
  const { nodeWidth, positions, graphWidth, graphHeight, edges } = layoutOntology(draft)
  const orphaned = draft.items.filter(item => !item.conceptId)
  const totalHeight = graphHeight + (orphaned.length ? orphaned.length * 38 + 38 : 0)
  useLayoutEffect(() => {
    const observer = new ResizeObserver(entries => { if (entries[0].contentRect.width > 0) setWidth(entries[0].contentRect.width) })
    if (viewport.current) observer.observe(viewport.current)
    return () => observer.disconnect()
  }, [])
  const fit = Math.min((width - 24) / graphWidth, 1)
  const scale = fit * zoom
  const activate = (kind: OntologySelection['kind'], id: string) => {
    const selection = { kind, id }
    return {
      role: 'button', tabIndex: 0, 'data-select': true, 'aria-pressed': selected.kind === kind && selected.id === id,
      onClick: () => onSelect(selection),
      onKeyDown: (event: React.KeyboardEvent<SVGGElement>) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(selection) }
      },
    }
  }
  return <div className="ontology-canvas-panel">
    <div className="ontology-canvas-toolbar"><div><span className="legend-dot class-dot" />类<span className="legend-line" />关系<span className="legend-line pending" />待确认</div>
      <div className="graph-tools">
        <button aria-label="缩小本体图" title="缩小" disabled={zoom <= .6} onClick={() => setZoom(Math.max(.6, zoom - .2))}>−</button>
        <output aria-label="画布缩放比例">{Math.round(scale * 100)}%</output>
        <button aria-label="放大本体图" title="放大" disabled={zoom >= 2.5} onClick={() => setZoom(Math.min(2.5, zoom + .2))}>＋</button>
        <button className="fit-button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }) }}>适应画布</button>
      </div>
    </div>
    <div ref={viewport} className="ontology-canvas" onPointerDown={event => {
      if (event.button !== 0 || (event.target as Element).closest('[data-select]')) return
      drag.current = { x: event.clientX, y: event.clientY, startX: pan.x, startY: pan.y }
      event.currentTarget.setPointerCapture(event.pointerId)
    }} onPointerMove={event => {
      if (drag.current) setPan({ x: drag.current.startX + event.clientX - drag.current.x, y: drag.current.startY + event.clientY - drag.current.y })
    }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}
      onLostPointerCapture={() => { drag.current = null }}>
      <svg width="100%" height={Math.max(430, totalHeight * fit + 30)} role="group" aria-label="完整本体图，点击类、属性或关系编辑">
        <defs>
          <marker id={`${marker}-arrow`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="context-stroke" strokeWidth="1.4" /></marker>
          <marker id={`${marker}-parent`} markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0 0L9 5L0 10Z" fill="white" stroke="#8b74b3" /></marker>
        </defs>
        <g transform={`translate(${12 + pan.x} ${14 + pan.y}) scale(${scale})`}>
          {edges.map(({ relation, d, labelX: x, labelY: y }) => {
            const active = selected.kind === 'relation' && selected.id === relation.id
            return <g key={relation.id} {...activate('relation', relation.id)} aria-label={`编辑关系 ${relation.name}`}
              className={`graph-relation ${relation.uncertain ? 'is-pending' : ''} ${active ? 'is-selected' : ''}`}>
              <title>{draft.classes.find(cls => cls.id === relation.sourceId)?.name} → {relation.name} → {draft.classes.find(cls => cls.id === relation.targetId)?.name}</title>
              <path className="edge-hit-area" d={d} />
              <path className="edge-visible" d={d} markerEnd={`url(#${marker}-arrow)`} />
              <rect className="edge-label-bg" x={x - 87} y={y - 25} width={174} height={51} rx={8} />
              <text className="edge-name" x={x} y={y - 3}>{label(relation.name, 11)}</text>
              <text className="edge-meta" x={x} y={y + 15}>{cardinalities[relation.cardinality]} · {relation.uncertain ? '待确认' : relation.edited ? '已编辑' : '有结构依据'}</text>
            </g>
          })}
          {draft.classes.filter(cls => cls.parentId).map(cls => {
            const a = positions.get(cls.id)!, b = positions.get(cls.parentId!)!
            return <g key={`parent-${cls.id}`} {...activate('class', cls.id)} aria-label={`编辑 ${cls.name} 的继承关系`} className="graph-parent">
              <path d={`M${a.x + nodeWidth / 2} ${a.y} L${b.x + nodeWidth / 2} ${b.y + b.height}`} markerEnd={`url(#${marker}-parent)`} />
              <text x={(a.x + b.x + nodeWidth) / 2} y={(a.y + b.y + b.height) / 2}>继承</text>
            </g>
          })}
          {draft.classes.map((cls, index) => {
            const p = positions.get(cls.id)!
            const active = selected.kind === 'class' && selected.id === cls.id
            return <g key={cls.id} className={`graph-class color-${index % 3}`}>
              <rect className={`class-frame ${active ? 'is-selected' : ''}`} x={p.x} y={p.y} width={nodeWidth} height={p.height} rx={12} />
              <g {...activate('class', cls.id)} aria-label={`编辑类 ${cls.name}`} className={`class-heading ${active ? 'is-selected' : ''}`}>
                <title>{cls.name} · {cls.description}</title>
                <rect className="node-hit" x={p.x + 1} y={p.y + 1} width={nodeWidth - 2} height={73} rx={11} />
                <text className="node-kind" x={p.x + 17} y={p.y + 23}>CLASS · {p.attributes.length} 个属性</text>
                <text className="node-name" x={p.x + 17} y={p.y + 51}>{label(cls.name)}</text>
                <text className="node-edit-icon" x={p.x + nodeWidth - 29} y={p.y + 50}>↗</text>
              </g>
              {p.attributes.length ? p.attributes.map((item, i) => <g key={item.id} {...activate('property', item.id)} aria-label={`编辑属性 ${item.name}`}
                className={`graph-property ${selected.kind === 'property' && selected.id === item.id ? 'is-selected' : ''} ${item.excluded ? 'is-excluded' : ''}`}>
                <title>{item.name} · {datatypes[item.datatype]} · {item.excluded ? '已排除' : item.uncertain ? '待确认' : '可纳入'}</title>
                <rect x={p.x + 5} y={p.y + 76 + i * 34} width={nodeWidth - 10} height={31} rx={5} />
                <text x={p.x + 17} y={p.y + 97 + i * 34}>{label(item.name, 10)}</text>
                <text className="property-type" x={p.x + nodeWidth - 15} y={p.y + 97 + i * 34}>
                  {item.excluded ? '已排除' : item.uncertain ? '待确认' : item.kind === 'calculated' ? '计算指标' : item.unit || datatypes[item.datatype]}</text>
              </g>) : <text className="node-empty" x={p.x + 17} y={p.y + 99}>暂无归属已确定的属性</text>}
            </g>
          })}
          {orphaned.length > 0 && <g className="unassigned-properties">
            <rect x={30} y={graphHeight} width={graphWidth - 65} height={orphaned.length * 38 + 28} rx={10} />
            {orphaned.map((item, index) => <g key={item.id} {...activate('property', item.id)} aria-label={`编辑待确认属性 ${item.name}`} className="unassigned-item">
              <rect x={40} y={graphHeight + 10 + index * 38} width={graphWidth - 85} height={35} rx={6} />
              <text x={56} y={graphHeight + 33 + index * 38}>{label(item.name)}</text>
              <text className="unassigned-caption" x={260} y={graphHeight + 33 + index * 38}>所属类待确认 · {item.sources.length} 个物理候选</text>
            </g>)}
          </g>}
        </g>
      </svg>
    </div>
    <div className="canvas-hint"><Icon name="info" size={15} /><span>点击类、属性或连线查看并编辑。拖动画布平移；Tab + Enter 也可选择。</span></div>
  </div>
}
