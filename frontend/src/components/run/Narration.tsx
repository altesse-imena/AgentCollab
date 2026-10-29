import { motion } from 'motion/react'
import { cx } from '../../lib/format'
import type { RunView, Tone } from '../../lib/runState'
import { narrate } from '../../lib/story'
import { Prose } from '../Prose'

const DOT: Record<Tone, string> = {
  neutral: 'bg-faint',
  info: 'bg-ultramarine-400',
  good: 'bg-emerald-400',
  warn: 'bg-amber-400',
  bad: 'bg-rose-400',
}

/** The big caption under the stage: what is happening right now, in one sentence. */
export function Narration({ view, mode }: { view: RunView; mode: 'live' | 'replay' | 'done' }) {
  const n = narrate(view)
  const running = view.status === 'running'
  return (
    <div className="min-h-[124px]">
      <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold tracking-[0.2em] text-faint uppercase">
        <span className="relative flex h-2 w-2">
          {running && (
            <span
              className={cx(
                'absolute inline-flex h-full w-full animate-ping rounded-full opacity-60',
                DOT[n.tone],
              )}
            />
          )}
          <span className={cx('relative inline-flex h-2 w-2 rounded-full', DOT[n.tone])} />
        </span>
        {running ? (mode === 'replay' ? 'Replaying' : 'Live') : 'Finished'}
      </div>
      <motion.div
        key={n.key}
        initial={{ opacity: 0, y: 12, filter: 'blur(4px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        <p className="font-heading text-2xl leading-snug text-ink md:text-3xl">{n.headline}</p>
        {n.detail && (
          <p className="mt-2 line-clamp-2 max-w-3xl text-sm leading-relaxed text-muted md:text-base">
            <Prose text={n.detail} />
          </p>
        )}
      </motion.div>
    </div>
  )
}

/** One segment per allowed round; the current one pulses while it runs. */
export function RoundProgress({ view }: { view: RunView }) {
  const total = Math.max(view.maxIterations, view.iteration, 1)
  const current =
    view.status === 'running'
      ? view.iteration + (view.nodes.write === 'running' ? 1 : 0)
      : view.iteration
  return (
    <div className="flex items-center gap-3">
      <div className="flex flex-1 gap-1.5">
        {Array.from({ length: total }, (_, i) => {
          const round = i + 1
          const done = round < current || (round === current && view.status !== 'running')
          const active = round === current && view.status === 'running'
          const passed = view.status === 'passed' && round === current
          return (
            <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
              <motion.div
                className={cx(
                  'h-full rounded-full',
                  passed ? 'bg-emerald-400' : done ? 'bg-amber-400/80' : 'bg-ultramarine-400',
                  active && 'animate-pulse',
                )}
                initial={false}
                animate={{ width: done || active ? '100%' : '0%' }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </div>
          )
        })}
      </div>
      <span className="shrink-0 text-xs text-faint">
        Round {Math.max(current, 1)} of {total}
      </span>
    </div>
  )
}
