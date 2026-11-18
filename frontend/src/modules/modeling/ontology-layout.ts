import type { OntologyDraft } from './state'

export function layoutOntology(draft: OntologyDraft, {showProperties = true}: {showProperties?: boolean} = {}) {
  const nodeWidth = 260
  const columns = Math.min(3, Math.max(1, draft.classes.length))
  const nodes = draft.classes.map(cls => {
    const properties = draft.items.filter(item => item.conceptId === cls.id)
    const attributes = showProperties ? properties : []
    return {id:cls.id, attributes, propertyCount:properties.length, height:showProperties ? 84 + Math.max(1, attributes.length) * 34 : 104}
  })
  const rowTops: number[] = []
  let top = 48
  for (let start = 0; start < nodes.length; start += columns) {
    rowTops.push(top)
    top += Math.max(...nodes.slice(start, start + columns).map(node => node.height)) + 130
  }
  const positions = new Map(nodes.map((node,index) => {
    const compact = nodes.length <= 3
    const x = compact ? index === 0 ? 40 : 610 : 40 + index % columns * 470
    const y = compact ? index === 0 ? 180 : 48 + (index - 1) * (Math.max(...nodes.map(node => node.height)) + 95) : rowTops[Math.floor(index / columns)]
    return [node.id, {...node,x,y}]
  }))
  const groups = new Map<string, string[]>()
  for (const relation of draft.relations) {
    const key = JSON.stringify([relation.sourceId, relation.targetId].sort())
    groups.set(key, [...groups.get(key) ?? [], relation.id])
  }
  const edges = draft.relations.flatMap(relation => {
    const source = positions.get(relation.sourceId), target = positions.get(relation.targetId)
    if (!source || !target) return []
    const group = groups.get(JSON.stringify([relation.sourceId, relation.targetId].sort()))!
    const lane = group.indexOf(relation.id)
    const right = target.x >= source.x
    const startX = source.x + (right ? nodeWidth : 0), endX = target.x + (right ? 0 : nodeWidth)
    const startY = source.y + source.height / 2, endY = target.y + target.height / 2
    const self = relation.sourceId === relation.targetId
    const offset = (lane - (group.length - 1) / 2) * 80
    const reach = 170 + lane * 260
    const d = self ? `M${startX} ${startY} C${startX + reach} ${startY - 150},${startX + reach} ${startY + 150},${startX} ${startY + 27}` :
      `M${startX} ${startY} C${startX + (right ? 145 : -145)} ${startY + offset * 4 / 3},${endX - (right ? 145 : -145)} ${endY + offset * 4 / 3},${endX} ${endY}`
    return [{ relation, d, labelX: self ? startX + 100 + lane * 190 : (startX + endX) / 2,
      labelY: self ? startY - 12 : (startY + endY) / 2 + offset,
      rightExtent: self ? startX + reach : Math.max(startX, endX) }]
  })
  const graphWidth = Math.max(600, ...[...positions.values()].map(node => node.x + nodeWidth + 50),
    ...edges.map(edge => Math.max(edge.rightExtent, edge.labelX + 87) + 28))
  const graphHeight = Math.max(400, ...[...positions.values()].map(item => item.y + item.height + 55),
    ...edges.map(edge => edge.labelY + 50))
  return { nodeWidth, positions, graphWidth, graphHeight, edges }
}

/** Automatic fit is separate from absolute zoom so dense models remain readable. */
export function canvasScale(graphWidth: number, graphHeight: number, width: number, height: number, manual: number | null) {
  return manual ?? Math.max(.01, Math.min((width - 48) / graphWidth, (height - 48) / graphHeight, 1))
}
