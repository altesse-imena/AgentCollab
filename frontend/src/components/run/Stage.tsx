import { Check, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { AGENTS, LINKS } from '../../lib/agents'
import { cx } from '../../lib/format'
import type { NodeId, NodeStatus } from '../../lib/runState'

type Point = { x: number; y: number }
interface Layout {
  width: number
  height: number
  vertical: boolean
  at: Record<string, Point>
}

// Horizontal on wide screens, top-to-bottom on phones
const WIDE: Layout = {
  width: 1200,
  height: 600,
  vertical: false,
  at: {
    gather_context: { x: 90, y: 300 },
    write: { x: 320, y: 300 },
    review: { x: 590, y: 120 },
    tests: { x: 590, y: 300 },
    security: { x: 590, y: 480 },
    run_tests: { x: 850, y: 300 },
    judge: { x: 1100, y: 300 },
  },
}
const TALL: Layout = {
  width: 480,
  height: 900,
  vertical: true,
  at: {
    gather_context: { x: 220, y: 70 },
    write: { x: 220, y: 230 },
    review: { x: 90, y: 420 },
    tests: { x: 220, y: 420 },
    security: { x: 350, y: 420 },
    run_tests: { x: 220, y: 610 },
    judge: { x: 220, y: 790 },
  },
}

const radius = (id: NodeId, vertical: boolean) => {
  const ai = AGENTS.find((a) => a.id === id)?.ai
  return vertical ? (ai ? 38 : 32) : ai ? 46 : 38
}

function linkPath(layout: Layout, from: NodeId, to: NodeId) {
  const a = layout.at[from]
  const b = layout.at[to]
  const ra = radius(from, layout.vertical)
  const rb = radius(to, layout.vertical)
  if (layout.vertical) {
    // start below the source's name label, end above the target's "AI agent" label
    const y1 = a.y + ra + 34
    const y2 = b.y - rb - (AGENTS.find((x) => x.id === to)?.ai ? 22 : 6)
    const mid = (y1 + y2) / 2
    return `M ${a.x} ${y1} C ${a.x} ${mid}, ${b.x} ${mid}, ${b.x} ${y2}`
  }
  const x1 = a.x + ra
  const x2 = b.x - rb
  const mid = (x1 + x2) / 2
  return `M ${x1} ${a.y} C ${mid} ${a.y}, ${mid} ${b.y}, ${x2} ${b.y}`
}

function feedbackPath(layout: Layout) {
  const j = layout.at.judge
  const w = layout.at.write
  if (layout.vertical) {
    const rj = radius('judge', true)
    const rw = radius('write', true)
    return `M ${j.x + rj} ${j.y} C ${layout.width - 10} ${j.y}, ${layout.width - 10} ${w.y}, ${w.x + rw} ${w.y}`
  }
  const rj = radius('judge', false)
  const rw = radius('write', false)
  return `M ${j.x} ${j.y - rj} C ${j.x} -40, ${w.x} -40, ${w.x} ${w.y - rw}`
}

const RING: Record<NodeStatus, string> = {
  idle: 'stroke-line-strong',
  running: 'stroke-brand-400',
  done: 'stroke-brand-500/35',
  failed: 'stroke-rose-400/80',
}
const ICON: Record<NodeStatus, string> = {
  idle: 'text-faint',
  running: 'text-accent',
  done: 'text-body',
  failed: 'text-rose-400',
}

export function Stage({
  nodes,
  iteration = 0,
  className,
}: {
  nodes: Record<NodeId, NodeStatus>
  iteration?: number
  className?: string
}) {
  const box = useRef<HTMLDivElement>(null)
  const [vertical, setVertical] = useState(false)
  const uid = useId().replace(/:/g, '')

  useEffect(() => {
    const el = box.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setVertical(entry.contentRect.width < 560))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const layout = vertical ? TALL : WIDE
  // The loop back to the Writer lights up while a later round is being written
  const reworking = iteration >= 1 && nodes.write === 'running'
  const looped = iteration > 1 || reworking

  return (
    <div ref={box} className={cx('relative w-full', className)}>
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label="The agents and how work flows between them"
      >
        <defs>
          <radialGradient id={`${uid}-glow`}>
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </radialGradient>
          <linearGradient id={`${uid}-active`} x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#6ee7b7" />
          </linearGradient>
        </defs>

        {/* Feedback loop: Judge back to Writer */}
        <g>
          <path
            id={`${uid}-feedback`}
            d={feedbackPath(layout)}
            fill="none"
            strokeWidth={2}
            strokeDasharray="6 8"
            className={cx(
              'transition-colors duration-500',
              looped ? 'stroke-amber-400/80' : 'stroke-line-strong/60',
            )}
          />
          {reworking &&
            [0, 0.6, 1.2].map((begin) => (
              <circle key={begin} r={4} className="fill-amber-300">
                <animateMotion dur="1.8s" begin={`${begin}s`} repeatCount="indefinite">
                  <mpath href={`#${uid}-feedback`} />
                </animateMotion>
              </circle>
            ))}
          {!layout.vertical && (
            <text
              x={(layout.at.judge.x + layout.at.write.x) / 2}
              y={22}
              textAnchor="middle"
              className={cx(
                'font-sans text-[13px] tracking-wide uppercase',
                looped ? 'fill-warn' : 'fill-faint',
              )}
            >
              {iteration > 1 ? `feedback loop · round ${iteration}` : 'feedback loop'}
            </text>
          )}
        </g>

        {/* Links between agents */}
        {LINKS.map(([from, to]) => {
          const id = `${uid}-${from}-${to}`
          const active = nodes[to] === 'running' && nodes[from] !== 'idle'
          const done = nodes[to] === 'done' || nodes[to] === 'failed'
          return (
            <g key={id}>
              <path
                id={id}
                d={linkPath(layout, from, to)}
                fill="none"
                strokeWidth={active ? 3 : 2}
                stroke={active ? `url(#${uid}-active)` : undefined}
                className={cx(
                  'transition-all duration-500',
                  !active && (done ? 'stroke-brand-500/30' : 'stroke-line-strong'),
                )}
              />
              {active &&
                [0, 0.45, 0.9].map((begin) => (
                  <circle key={begin} r={4.5} className="fill-brand-300">
                    <animateMotion dur="1.35s" begin={`${begin}s`} repeatCount="indefinite">
                      <mpath href={`#${id}`} />
                    </animateMotion>
                  </circle>
                ))}
            </g>
          )
        })}

        {/* Agents */}
        {AGENTS.map((agent) => {
          const p = layout.at[agent.id]
          const r = radius(agent.id, layout.vertical)
          const status = nodes[agent.id]
          const Icon = agent.icon
          const iconSize = agent.ai ? r * 0.82 : r * 0.78
          return (
            <g key={agent.id} transform={`translate(${p.x} ${p.y})`}>
              {status === 'running' && (
                <>
                  <circle r={r * 2.1} fill={`url(#${uid}-glow)`} className="stage-breathe" />
                  <circle
                    r={r + 9}
                    fill="none"
                    strokeWidth={2}
                    strokeDasharray="4 10"
                    strokeLinecap="round"
                    className="stage-spin stroke-brand-300"
                  />
                </>
              )}
              <circle
                r={r}
                strokeWidth={status === 'idle' ? 1.5 : 2.5}
                className={cx('fill-canvas transition-all duration-500', RING[status])}
              />
              {agent.ai && (
                <circle
                  r={r - 7}
                  fill="none"
                  strokeWidth={1}
                  className={cx(
                    'transition-all duration-500',
                    status === 'running' ? 'stroke-brand-400/50' : 'stroke-line/80',
                  )}
                />
              )}
              <Icon
                x={-iconSize / 2}
                y={-iconSize / 2}
                width={iconSize}
                height={iconSize}
                strokeWidth={1.6}
                className={cx('transition-colors duration-500', ICON[status])}
              />
              {(status === 'done' || status === 'failed') && (
                <g transform={`translate(${r * 0.72} ${-r * 0.72})`}>
                  <circle
                    r={11}
                    className={status === 'done' ? 'fill-brand-600' : 'fill-rose-500'}
                  />
                  {status === 'done' ? (
                    <Check
                      x={-7}
                      y={-7}
                      width={14}
                      height={14}
                      strokeWidth={3}
                      className="text-white"
                    />
                  ) : (
                    <X
                      x={-7}
                      y={-7}
                      width={14}
                      height={14}
                      strokeWidth={3}
                      className="text-white"
                    />
                  )}
                </g>
              )}
              <text
                y={r + 26}
                textAnchor="middle"
                className={cx(
                  'font-heading text-[19px] transition-colors duration-500',
                  status === 'idle' ? 'fill-muted' : 'fill-ink',
                )}
              >
                {agent.name}
              </text>
              {!layout.vertical && (
                <text y={r + 46} textAnchor="middle" className="fill-faint font-sans text-[13px]">
                  {agent.role}
                </text>
              )}
              {agent.ai && (
                <text
                  y={-r - 12}
                  textAnchor="middle"
                  className={cx(
                    'font-sans text-[10px] font-semibold tracking-[0.2em]',
                    status === 'running' ? 'fill-accent' : 'fill-faint',
                  )}
                >
                  AI AGENT
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
