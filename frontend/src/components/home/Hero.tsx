import { ArrowRight, BookOpen } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { NODES, type NodeId, type NodeStatus } from '../../lib/runState'
import type { Showcase } from '../../lib/story'
import { formatDuration } from '../../lib/story'
import { Stage } from '../run/Stage'

// A loop of one round, so the hero shows the agents at work without a real run
const PHASES: [running: NodeId[], done: NodeId[]][] = [
  [['gather_context'], []],
  [['write'], ['gather_context']],
  [
    ['review', 'tests', 'security'],
    ['gather_context', 'write'],
  ],
  [['run_tests'], ['gather_context', 'write', 'review', 'tests', 'security']],
  [['judge'], ['gather_context', 'write', 'review', 'tests', 'security', 'run_tests']],
  [[], ['gather_context', 'write', 'review', 'tests', 'security', 'run_tests', 'judge']],
]

function useAmbientNodes() {
  const [phase, setPhase] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setPhase((p) => (p + 1) % PHASES.length), 1700)
    return () => clearInterval(timer)
  }, [])
  const [running, done] = PHASES[phase]
  return Object.fromEntries(
    NODES.map((n) => [n, running.includes(n) ? 'running' : done.includes(n) ? 'done' : 'idle']),
  ) as Record<NodeId, NodeStatus>
}

const SNIPPETS = [
  'review = await reviewer.inspect(diff)',
  'if not tests.passed: feedback.append(failures)',
  "graph.add_edge('write', 'security')",
  'sandbox.run(network=False, read_only=True)',
  'judge.verdict(review, tests, findings)',
  'cursor.execute(query, (user_id,))',
  'budget.check()  # stop before overspending',
  'state.iteration += 1',
  'findings = security.scan(patch)',
  'assert slugify("Hello World") == "hello-world"',
]

function DriftingCode() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
      {SNIPPETS.map((s, i) => (
        <span
          key={s}
          className="code-drift absolute font-mono text-xs whitespace-nowrap text-ultramarine-500/25 md:text-sm dark:text-ultramarine-400/20"
          style={
            {
              left: `${(i * 37) % 85}%`,
              top: `${8 + ((i * 53) % 84)}%`,
              '--drift-duration': `${20 + (i % 4) * 5}s`,
              '--drift-delay': `${-i * 2.3}s`,
            } as React.CSSProperties
          }
        >
          {s}
        </span>
      ))}
    </div>
  )
}

export function Hero({
  stats,
  onWatch,
  onStory,
}: {
  stats: Showcase
  onWatch?: () => void
  onStory?: () => void
}) {
  const nodes = useAmbientNodes()
  const figures = [
    ['4', 'AI agents per run'],
    [stats.finished ? `${Math.round(stats.passRate * 100)}%` : '–', 'of recorded runs pass'],
    [stats.finished ? `$${stats.avgCost.toFixed(3)}` : '–', 'average cost per run'],
    [stats.avgSeconds ? formatDuration(stats.avgSeconds) : '–', 'average time to a result'],
  ]
  return (
    <section className="relative isolate overflow-hidden px-4 pt-16 pb-12 md:px-8 md:pt-24">
      <DriftingCode />
      <div className="pointer-events-none absolute top-0 right-0 -z-10 h-2/3 w-2/3 bg-radial from-ultramarine-500/10 to-transparent to-70%" />
      <div className="mx-auto max-w-6xl text-center">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-4 py-1.5 text-xs font-medium text-muted backdrop-blur-sm"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-ultramarine-400" />
          Multi-agent coding with LangGraph
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mx-auto mt-6 max-w-4xl text-5xl leading-[1.05] text-ink md:text-7xl"
        >
          Four AI agents.{' '}
          <span className="gradient-text">One change that&nbsp;survives review.</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted md:text-xl"
        >
          A writer drafts the code. A reviewer, a tester and a security analyst tear it apart in
          parallel. A judge sends it back until it passes, or the rounds run out.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          {onWatch && (
            <button
              type="button"
              onClick={onWatch}
              className="pill-primary group px-6 py-3 text-sm"
            >
              Watch a run
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
          )}
          {onStory && (
            <button type="button" onClick={onStory} className="pill-outline px-6 py-3 text-sm">
              <BookOpen className="h-4 w-4" /> Read a case study
            </button>
          )}
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.9, delay: 0.35 }}
        className="relative mx-auto mt-14 max-w-6xl"
      >
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_50%_50%,rgba(65,102,245,0.18),transparent_60%)]" />
        <Stage nodes={nodes} />
      </motion.div>

      <dl className="mx-auto mt-14 grid max-w-5xl grid-cols-2 gap-x-6 gap-y-8 border-t border-line pt-10 md:grid-cols-4">
        {figures.map(([value, label]) => (
          <div key={label} className="text-center">
            <dd className="font-heading text-4xl text-ink md:text-5xl">{value}</dd>
            <dt className="mt-2 text-sm text-faint">{label}</dt>
          </div>
        ))}
      </dl>
    </section>
  )
}
