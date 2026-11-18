import type { OntologyDraft } from './state'

export function layoutOntology(draft: OntologyDraft) {
  const nodeWidth = 240
  const positions = new Map(draft.classes.map((cls, index) => {
    const x = draft.classes.length <= 3 ? index === 0 ? 30 : 545 : 30 + (index % 3) * 280
    const y = draft.classes.length <= 3 ? index === 0 ? 205 : 50 + (index - 1) * 295 : 45 + Math.floor(index / 3) * 245
    const attributes = draft.items.filter(item => item.conceptId === cls.id)
    return [cls.id, { x, y, attributes, height: 83 + Math.max(1, attributes.length) * 34 }]
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
  const graphWidth = Math.max(draft.classes.length <= 3 ? 820 : 850,
    ...edges.map(edge => Math.max(edge.rightExtent, edge.labelX + 87) + 28))
  const graphHeight = Math.max(565, ...[...positions.values()].map(item => item.y + item.height + 55),
    ...edges.map(edge => edge.labelY + 50))
  return { nodeWidth, positions, graphWidth, graphHeight, edges }
}
