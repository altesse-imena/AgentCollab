import { ArrowLeft, BookOpen, ChevronDown, Play, RotateCcw, SkipForward } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { useRunEvents } from '../../lib/api'
import { cx } from '../../lib/format'
import { firstSentence, KIND_LABEL, taskFor, titleFor } from '../../lib/story'
import type { Task } from '../../lib/types'
import { api } from '../../lib/api'
import { Prose } from '../Prose'
import { RoundDetails } from '../RoundDetails'
import { StatsBar } from '../StatsBar'
import { Timeline } from '../Timeline'
import { Panel } from '../ui'
import { AgentCards } from './AgentCards'
import { Narration, RoundProgress } from './Narration'
import { Stage } from './Stage'
import { Story } from './Story'

export type RunMode = 'watch' | 'story'
const SPEEDS = [1, 4, 16]
const DEFAULT_REPLAY_SPEED = 4

export function RunPage({
  runId,
  mode,
  initialSpeed,
  tasks,
  onMode,
}: {
  runId: string
  mode: RunMode
  initialSpeed: number | null
  tasks: Task[]
  onMode: (mode: RunMode) => void
}) {
  // Finished runs replay on their own when watched; live runs stream as they happen.
  // The page remounts on every route change, so the initial value covers story mode and
  // links with a fixed speed; otherwise the run's status decides once it's known.
  const [speed, setSpeed] = useState<number | null>(mode === 'story' ? 0 : initialSpeed)
  const [nonce, setNonce] = useState(0)
  const decided = speed !== null

  useEffect(() => {
    if (decided) return
    let cancelled = false
    api
      .run(runId)
      .then((r) => !cancelled && setSpeed(r.status === 'running' ? 0 : DEFAULT_REPLAY_SPEED))
      .catch(() => !cancelled && setSpeed(0))
    return () => {
      cancelled = true
    }
  }, [runId, decided])

  const { view, connected } = useRunEvents(speed === null ? null : runId, speed ?? 0, nonce)
  const finished = !['waiting', 'running'].includes(view.status)
  const replaying = (speed ?? 0) > 0 && !finished
  const task = taskFor(view.task, tasks)
  const title = titleFor(view.task, tasks)

  const replay = (s: number) => {
    setSpeed(s)
    setNonce((n) => n + 1)
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-6 pb-24 md:px-8 md:pt-10">
      <a href="#/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> All runs
      </a>

      <header className="mt-6 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold tracking-[0.2em] text-accent uppercase">
            {task ? KIND_LABEL[task.kind] : 'Run'} ·{' '}
            {mode === 'story' ? 'Case study' : 'Watch the agents'}
          </p>
          <h2 className="mt-2 text-4xl text-ink md:text-5xl">{title}</h2>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted md:text-lg">
            <Prose text={firstSentence(view.task) || 'Loading…'} />
          </p>
        </div>
        <div className="flex shrink-0 rounded-full border border-line bg-card p-1 backdrop-blur-sm">
          {(
            [
              ['watch', 'Watch', Play],
              ['story', 'Story', BookOpen],
            ] as const
          ).map(([m, label, Icon]) => (
            <button
              key={m}
              type="button"
              onClick={() => onMode(m)}
              className={cx(
                'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all duration-300',
                mode === m
                  ? 'bg-ultramarine-600 text-white shadow-lg shadow-ultramarine-600/30'
                  : 'text-muted hover:text-ink',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </header>

      <div className="mt-10">
        {mode === 'watch' ? (
          <>
            <section className="relative overflow-hidden rounded-3xl border border-line bg-card px-4 pt-10 pb-6 backdrop-blur-sm md:px-10">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_45%,rgba(65,102,245,0.14),transparent_65%)]" />
              <Stage nodes={view.nodes} iteration={view.iteration} className="relative" />
              <div className="relative mt-8 border-t border-line pt-6">
                <Narration view={view} mode={replaying ? 'replay' : finished ? 'done' : 'live'} />
                <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-center">
                  <div className="flex-1">
                    <RoundProgress view={view} />
                  </div>
                  {(finished || replaying) && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => replay(speed || DEFAULT_REPLAY_SPEED)}
                        className="pill-outline px-3 py-1.5 text-xs"
                      >
                        <RotateCcw className="h-3.5 w-3.5" /> Replay
                      </button>
                      {SPEEDS.map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => replay(s)}
                          className={cx(
                            'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                            replaying && speed === s
                              ? 'bg-ultramarine-600 text-white'
                              : 'text-muted hover:bg-hover hover:text-ink',
                          )}
                        >
                          {s}×
                        </button>
                      ))}
                      {replaying && (
                        <button
                          type="button"
                          onClick={() => replay(0)}
                          className="rounded-full px-3 py-1.5 text-xs font-medium text-muted hover:bg-hover hover:text-ink"
                        >
                          <SkipForward className="inline h-3.5 w-3.5" /> Skip to end
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>
            <div className="mt-6">
              <AgentCards view={view} />
            </div>
            {finished && (
              <div className="mt-8 flex justify-center">
                <button
                  type="button"
                  onClick={() => onMode('story')}
                  className="pill-primary group px-6 py-3 text-sm"
                >
                  <BookOpen className="h-4 w-4" /> Read it as a story
                </button>
              </div>
            )}
          </>
        ) : (
          <Story view={view} />
        )}
      </div>

      <UnderTheHood>
        <div className="space-y-4">
          <Panel>
            <StatsBar view={view} connected={connected} replaying={replaying} />
          </Panel>
          <div className="grid gap-4 *:min-w-0 lg:grid-cols-[360px_1fr]">
            <Panel title="Every event" className="flex max-h-[560px] min-h-0 flex-col">
              <div className="min-h-0 flex-1">
                <Timeline items={view.timeline} />
              </div>
            </Panel>
            <Panel title="Raw output" className="flex max-h-[560px] min-h-[320px] flex-col">
              <RoundDetails rounds={view.rounds} />
            </Panel>
          </div>
        </div>
      </UnderTheHood>
    </div>
  )
}

function UnderTheHood({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <section className="mt-16">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="group flex w-full items-center gap-4 text-left"
      >
        <span className="h-px flex-1 bg-line" />
        <span className="inline-flex items-center gap-2 text-sm font-medium text-muted group-hover:text-ink">
          Under the hood: tokens, cost, every event, raw diffs
          <ChevronDown
            className={cx('h-4 w-4 transition-transform duration-300', open && 'rotate-180')}
          />
        </span>
        <span className="h-px flex-1 bg-line" />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="pt-6">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
