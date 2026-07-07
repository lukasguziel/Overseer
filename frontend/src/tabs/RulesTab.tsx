import { createContext, useContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap, Handle, Position,
  addEdge, applyNodeChanges, applyEdgeChanges,
  type Node, type Edge, type Connection, type NodeChange, type EdgeChange, type NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { call } from '../api'
import type { GroupRuleJson } from '../types'

// Kontext, damit Node-Komponenten ihre Daten aktualisieren koennen (ohne
// Funktionen in node.data zu speichern -> saubere Serialisierung).
interface GraphApi {
  update: (id: string, patch: Record<string, unknown>) => void
  remove: (id: string) => void
}
const GraphCtx = createContext<GraphApi>({ update: () => {}, remove: () => {} })

const CATEGORIES = ['light', 'camera', 'mesh', 'spline', 'null', 'other']

function csv(s: string | undefined): string[] {
  return (s || '').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean)
}

function NodeShell({ id, title, color, children }: {
  id: string; title: string; color: string; children: ReactNode
}) {
  const { remove } = useContext(GraphCtx)
  return (
    <div className="rf-node" style={{ borderColor: color }}>
      <div className="rf-head" style={{ background: color }}>
        <span>{title}</span>
        <button className="rf-x" onClick={() => remove(id)}>×</button>
      </div>
      <div className="rf-body">{children}</div>
    </div>
  )
}

function KeywordNode({ id, data }: NodeProps) {
  const { update } = useContext(GraphCtx)
  return (
    <NodeShell id={id} title="Keywords" color="#5b9dff">
      <textarea rows={2} value={data.keywords || ''} placeholder="chair, table, sofa"
        onChange={(e) => update(id, { keywords: e.target.value })} />
      <Handle type="source" position={Position.Right} />
    </NodeShell>
  )
}

function CategoryNode({ id, data }: NodeProps) {
  const { update } = useContext(GraphCtx)
  return (
    <NodeShell id={id} title="Category" color="#b07bff">
      <select value={data.category || 'mesh'} onChange={(e) => update(id, { category: e.target.value })}>
        {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <Handle type="source" position={Position.Right} />
    </NodeShell>
  )
}

function GroupNode({ id, data }: NodeProps) {
  const { update } = useContext(GraphCtx)
  return (
    <NodeShell id={id} title="Group (target)" color="#3fb27f">
      <Handle type="target" position={Position.Left} />
      <label>Name<input value={data.name || ''} placeholder="Furniture"
        onChange={(e) => update(id, { name: e.target.value })} /></label>
      <label>Aliases<input value={data.aliases || ''} placeholder="moebel"
        onChange={(e) => update(id, { aliases: e.target.value })} /></label>
      <label>Priority<input type="number" value={data.priority ?? 50}
        onChange={(e) => update(id, { priority: Number(e.target.value) })} /></label>
    </NodeShell>
  )
}

const nodeTypes = { keyword: KeywordNode, category: CategoryNode, group: GroupNode }

type NodeKind = keyof typeof nodeTypes

function graphToGroups(nodes: Node[], edges: Edge[]): GroupRuleJson[] {
  interface Agg {
    name: string
    priority: number
    keywords: Set<string>
    categories: Set<string>
    aliases: string[]
  }
  const groups: Record<string, Agg> = {}
  nodes.filter((n) => n.type === 'group').forEach((g) => {
    groups[g.id] = {
      name: g.data.name || 'Group',
      priority: Number(g.data.priority) || 0,
      keywords: new Set(),
      categories: new Set(),
      aliases: csv(g.data.aliases),
    }
  })
  edges.forEach((e) => {
    const g = groups[e.target]
    const src = nodes.find((n) => n.id === e.source)
    if (!g || !src) return
    if (src.type === 'keyword') csv(src.data.keywords).forEach((k) => g.keywords.add(k))
    if (src.type === 'category') g.categories.add(src.data.category || 'mesh')
  })
  return Object.values(groups).map((g) => ({
    name: g.name, priority: g.priority,
    keywords: [...g.keywords], categories: [...g.categories], aliases: g.aliases,
  }))
}

export default function RulesTab() {
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [status, setStatus] = useState('Loading rules …')
  const [rawConfig, setRawConfig] = useState<Record<string, unknown>>({})
  const idRef = useRef(1)

  const update = useCallback((id: string, patch: Record<string, unknown>) => {
    setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)))
  }, [])
  const remove = useCallback((id: string) => {
    setNodes((ns) => ns.filter((n) => n.id !== id))
    setEdges((es) => es.filter((e) => e.source !== id && e.target !== id))
  }, [])

  useEffect(() => {
    call('config').then((r) => {
      const cfg = r.config || {}
      setRawConfig(cfg)
      if (cfg.graph && Array.isArray(cfg.graph.nodes)) {
        setNodes(cfg.graph.nodes)
        setEdges(cfg.graph.edges || [])
        const maxId = (cfg.graph.nodes as Node[]).reduce((m, n) => {
          const num = parseInt(String(n.id).split('_')[1] || '0', 10)
          return Math.max(m, num)
        }, 0)
        idRef.current = maxId + 1
        setStatus('Rules loaded.')
      } else {
        setStatus('Empty graph — add and connect nodes.')
      }
    }).catch((e) => setStatus('Error: ' + e.message))
  }, [])

  const onNodesChange = useCallback((ch: NodeChange[]) => setNodes((ns) => applyNodeChanges(ch, ns)), [])
  const onEdgesChange = useCallback((ch: EdgeChange[]) => setEdges((es) => applyEdgeChanges(ch, es)), [])
  const onConnect = useCallback((p: Connection) => setEdges((es) => addEdge({ ...p, animated: true }, es)), [])

  const addNode = (type: NodeKind) => {
    const id = `${type}_${idRef.current++}`
    const defaults: Record<NodeKind, Record<string, unknown>> = {
      keyword: { keywords: '' },
      category: { category: 'mesh' },
      group: { name: '', aliases: '', priority: 50 },
    }
    const pos = { x: type === 'group' ? 420 : 60, y: 40 + (idRef.current % 8) * 90 }
    setNodes((ns) => ns.concat({ id, type, position: pos, data: defaults[type] }))
  }

  const save = async () => {
    setStatus('Saving …')
    try {
      const groups = graphToGroups(nodes, edges)
      const data = { ...rawConfig, groups, graph: { nodes, edges } }
      await call('config', { save: true, data })
      setRawConfig(data)
      setStatus(`Saved: ${groups.length} groups -> config.json`)
    } catch (e: any) {
      setStatus('Error: ' + e.message)
    }
  }

  return (
    <GraphCtx.Provider value={{ update, remove }}>
      <div className="rf-toolbar">
        <button onClick={() => addNode('keyword')}>+ Keyword</button>
        <button onClick={() => addNode('category')}>+ Category</button>
        <button onClick={() => addNode('group')}>+ Group</button>
        <button className="apply" onClick={save}>Save → config.json</button>
        <span className="status">{status}</span>
      </div>
      <div className="rf-canvas">
        <ReactFlow
          nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
          fitView
        >
          <Background color="#34383f" gap={18} />
          <MiniMap pannable zoomable style={{ background: '#24262b' }} />
          <Controls />
        </ReactFlow>
      </div>
      <p className="rf-hint">
        Connect <b>Keyword</b> and <b>Category</b> nodes to a <b>Group</b> node.
        Matching objects are assigned to that group. “Save” writes the
        rules to config.json (the plugin uses them immediately).
      </p>
    </GraphCtx.Provider>
  )
}
