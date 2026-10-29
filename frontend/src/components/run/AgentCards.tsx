import { motion } from 'motion/react'
import { AGENT_BY_ID } from '../../lib/agents'
import { cx } from '../../lib/format'
import type { NodeId, RunView, Tone } from '../../lib/runState'
import { speechFor } from '../../lib/story'
import { Prose } from '../Prose'

const CAST: NodeId[] = ['write', 'review', 'tests', 'security']

const STATUS_TEXT: Record<Tone, string> = {
  neutral: 'text-faint',
  info: 'text-accent',
  good: 'text-good',
  warn: 'text-warn',
  bad: 'text-bad',
}

/** What each AI agent concluded this round, in its own words. */
export function AgentCards({ view }: { view: RunView }) {
  const round = view.rounds[view.rounds.length - 1]
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {CAST.map((id, i) => {
        const agent = AGENT_BY_ID[id]!
        const running = view.nodes[id] === 'running'
        const speech = speechFor(id, round, running)
        const Icon = agent.icon
        return (
          <motion.div
            key={id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i, duration: 0.4 }}
            className={cx(
              'relative overflow-hidden rounded-2xl border bg-card p-5 backdrop-blur-sm transition-all duration-500',
              running
                ? 'border-brand-400/60 shadow-[0_0_40px_-8px] shadow-brand-500/50'
                : 'border-line',
            )}
          >
            {running && (
              <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-brand-400 to-transparent" />
            )}
            <div className="flex items-center gap-3">
              <span
                className={cx(
                  'flex h-10 w-10 items-center justify-center rounded-full border transition-colors duration-500',
                  running
                    ? 'border-brand-400/60 bg-brand-500/15 text-accent'
                    : 'border-line bg-sunken text-muted',
                )}
              >
                <Icon className="h-5 w-5" strokeWidth={1.75} />
              </span>
              <div className="min-w-0">
                <p className="font-heading text-lg leading-tight text-ink">{agent.name}</p>
                <p className="text-xs text-faint">{agent.role}</p>
              </div>
            </div>
            <motion.div
              key={`${round?.iteration ?? 0}-${speech.status}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <p className={cx('mt-4 text-sm font-medium', STATUS_TEXT[speech.tone])}>
                {running ? <Thinking /> : speech.status}
              </p>
              {speech.quote && !running && (
                <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-body">
                  “<Prose text={speech.quote} />”
                </p>
              )}
            </motion.div>
          </motion.div>
        )
      })}
    </div>
  )
}

function Thinking() {
  return (
    <span className="inline-flex items-center gap-1.5">
      Thinking
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block h-1 w-1 rounded-full bg-current"
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </span>
  )
}
