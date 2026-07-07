// Pure conversion between the React Flow graph (RulesTab canvas) and the
// nested structure tree stored in config.structure. Kept free of React so
// it is unit-testable. Group->group edges (source = child group, target =
// parent group) encode the parent relationship of nested groups.
import type { Node, Edge } from 'reactflow'
import type { StructureNode } from '../types'

export function csv(s: string | undefined): string[] {
  return (s || '').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean)
}

// Graph -> nested structure tree. Keyword/Category source nodes feed a group's
// match; a group wired into another group's target handle becomes its child.
export function graphToStructure(nodes: Node[], edges: Edge[]): StructureNode[] {
  const node = new Map<string, StructureNode>()
  const kw = new Map<string, Set<string>>()
  const cat = new Map<string, Set<string>>()

  nodes.filter((n) => n.type === 'group').forEach((g) => {
    node.set(g.id, {
      name: g.data.name || 'Group',
      aliases: csv(g.data.aliases),
      priority: Number(g.data.priority) || 0,
      children: [],
    })
    kw.set(g.id, new Set())
    cat.set(g.id, new Set())
  })

  const parentOf = new Map<string, string>()   // childGroupId -> parentGroupId
  edges.forEach((e) => {
    if (!node.has(e.target)) return
    const src = nodes.find((n) => n.id === e.source)
    if (!src) return
    if (src.type === 'keyword') csv(src.data.keywords).forEach((k) => kw.get(e.target)!.add(k))
    else if (src.type === 'category') cat.get(e.target)!.add(src.data.category || 'mesh')
    else if (src.type === 'group' && node.has(src.id) && src.id !== e.target) parentOf.set(src.id, e.target)
  })

  node.forEach((n, id) => {
    const kws = [...kw.get(id)!]
    const cats = [...cat.get(id)!]
    if (kws.length) n.keywords = kws
    if (cats.length) n.categories = cats
    if (!n.aliases || n.aliases.length === 0) delete n.aliases
  })

  const roots: StructureNode[] = []
  node.forEach((n, id) => {
    const p = parentOf.get(id)
    if (p && node.has(p)) node.get(p)!.children!.push(n)
    else roots.push(n)
  })
  node.forEach((n) => { if (n.children && n.children.length === 0) delete n.children })
  return roots
}

// Nested structure tree -> graph (used when a config carries structure but no
// saved graph layout). Deterministic ids so a round-trip stays stable.
export function structureToGraph(structure: StructureNode[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []
  let seq = 0

  const walk = (list: StructureNode[], parentId: string | null, depth: number) => {
    list.forEach((g, i) => {
      const id = `group_${++seq}`
      const baseX = 140 + depth * 340
      const baseY = 40 + (nodes.filter((n) => n.type === 'group').length) * 140 + i * 0
      nodes.push({
        id, type: 'group',
        position: { x: baseX, y: baseY },
        data: { name: g.name, aliases: (g.aliases || []).join(', '), priority: g.priority ?? 50 },
      })
      if (parentId) edges.push({ id: `e_${id}_${parentId}`, source: id, target: parentId, animated: true })

      if (g.keywords && g.keywords.length) {
        const kid = `keyword_${++seq}`
        nodes.push({ id: kid, type: 'keyword', position: { x: baseX - 240, y: baseY }, data: { keywords: g.keywords.join(', ') } })
        edges.push({ id: `e_${kid}_${id}`, source: kid, target: id, animated: true })
      }
      ;(g.categories || []).forEach((c, ci) => {
        const cid = `category_${++seq}`
        nodes.push({ id: cid, type: 'category', position: { x: baseX - 240, y: baseY + 90 + ci * 70 }, data: { category: c } })
        edges.push({ id: `e_${cid}_${id}`, source: cid, target: id, animated: true })
      })
      if (g.children && g.children.length) walk(g.children, id, depth + 1)
    })
  }
  walk(structure, null, 0)
  return { nodes, edges }
}
