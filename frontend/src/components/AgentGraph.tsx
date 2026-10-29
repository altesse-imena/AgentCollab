import {
  Background,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { memo, useMemo } from 'react'
import { cx } from '../lib/format'
import { NODE_LABELS, type NodeId, type NodeStatus, type RunView } from '../lib/runState'

const ROLE: Record<NodeId, string> = {
  gather_context: 'picks relevant files',
  write: 'writes the change',
  review: 'reviews the diff',
  tests: 'writes tests',
  security: 'checks for vulnerabilities',
  run_tests: 'runs tests in a sandbox',
  judge: 'pass or send feedback',
  finalize: 'returns the result',
}

const AI_NODES = new Set<NodeId>(['write', 'review', 'tests', 'security'])

const POSITIONS: Record<NodeId, { x: number; y: number }> = {
  gather_context: { x: 0, y: 140 },
  write: { x: 220, y: 140 },
  review: { x: 460, y: 20 },
  tests: { x: 460, y: 140 },
  security: { x: 460, y: 260 },
  run_tests: { x: 700, y: 140 },
  judge: { x: 920, y: 140 },
  finalize: { x: 1140, y: 140 },
}

const STATUS_STYLE: Record<NodeStatus, string> = {
  idle: 'border-slate-700 bg-slate-900 text-slate-400',
  running: 'border-brand-400 bg-brand-500/15 text-white shadow-[0_0_24px] shadow-brand-500/40',
  done: 'border-emerald-500/60 bg-emerald-500/10 text-emerald-100',
  failed: 'border-rose-500/70 bg-rose-500/10 text-rose-100',
}

type AgentNodeData = { id: NodeId; status: NodeStatus }

const AgentNode = memo(function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  const { id, status } = data
  return (
    <div
      className={cx(
        'w-[170px] rounded-xl border px-3 py-2.5 transition-all duration-300',
        STATUS_STYLE[status],
      )}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <Handle type="target" id="top" position={Position.Top} className="!opacity-0" />
      <div className="flex items-center gap-2">
        <span
          className={cx(
            'h-2 w-2 shrink-0 rounded-full',
            status === 'running' && 'animate-pulse bg-brand-300',
            status === 'done' && 'bg-emerald-400',
            status === 'failed' && 'bg-rose-400',
            status === 'idle' && 'bg-slate-600',
          )}
        />
        <span className="text-[13px] font-semibold">{NODE_LABELS[id]}</span>
        {AI_NODES.has(id) && (
          <span className="ml-auto rounded bg-white/10 px-1 text-[9px] font-medium uppercase tracking-wide">
            AI
          </span>
        )}
      </div>
      <p className="mt-0.5 text-[11px] opacity-70">{ROLE[id]}</p>
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <Handle type="source" id="top" position={Position.Top} className="!opacity-0" />
    </div>
  )
})

const nodeTypes = { agent: AgentNode }

const LINKS: [NodeId, NodeId][] = [
  ['gather_context', 'write'],
  ['write', 'review'],
  ['write', 'tests'],
  ['write', 'security'],
  ['review', 'run_tests'],
  ['tests', 'run_tests'],
  ['security', 'run_tests'],
  ['run_tests', 'judge'],
  ['judge', 'finalize'],
]

export function AgentGraph({ view }: { view: RunView }) {
  const nodes = useMemo<Node<AgentNodeData>[]>(
    () =>
      (Object.keys(POSITIONS) as NodeId[]).map((id) => ({
        id,
        type: 'agent',
        position: POSITIONS[id],
        data: { id, status: view.nodes[id] },
        draggable: false,
      })),
    [view.nodes],
  )

  const edges = useMemo<Edge[]>(() => {
    const color = (target: NodeId) =>
      view.nodes[target] === 'running' ? '#6985f7' : view.nodes[target] === 'idle' ? '#334155' : '#10b98199'
    const base = LINKS.map(([source, target]) => ({
      id: `${source}-${target}`,
      source,
      target,
      animated: view.nodes[target] === 'running',
      style: { stroke: color(target), strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: color(target) },
    }))
    const looping = view.iteration > 1 || view.nodes.judge === 'done'
    return [
      ...base,
      {
        id: 'feedback',
        source: 'judge',
        sourceHandle: 'top',
        target: 'write',
        targetHandle: 'top',
        type: 'smoothstep',
        label: view.iteration > 1 ? `feedback · round ${view.iteration}` : 'feedback',
        labelStyle: { fill: '#94a3b8', fontSize: 11 },
        labelBgStyle: { fill: '#0f172a' },
        style: {
          stroke: looping ? '#f59e0b99' : '#334155',
          strokeDasharray: '5 5',
          strokeWidth: 1.5,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: looping ? '#f59e0b99' : '#334155' },
      },
    ]
  }, [view.nodes, view.iteration])

  return (
    <div className="h-[300px] w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.06 }}
        style={{ background: 'transparent' }}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        colorMode="dark"
      >
        <Background color="#1e293b" gap={20} bgColor="transparent" />
      </ReactFlow>
    </div>
  )
}
