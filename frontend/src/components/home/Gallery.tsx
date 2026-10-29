import {
  BookOpen,
  Bug,
  CircleCheck,
  CircleX,
  type LucideIcon,
  Play,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { cx, timeAgo, usd } from '../../lib/format'
import {
  firstSentence,
  formatDuration,
  humanize,
  KIND_LABEL,
  taskFor,
  titleFor,
} from '../../lib/story'
import type { RunSummary, Task } from '../../lib/types'
import { Prose } from '../Prose'

type Kind = Task['kind']
const KIND_STYLE: Record<Kind, { gradient: string; icon: LucideIcon }> = {
  feature: { gradient: 'from-ultramarine-600 via-ultramarine-500 to-sky-500', icon: Sparkles },
  bug: { gradient: 'from-amber-500 via-orange-500 to-rose-500', icon: Bug },
  security: { gradient: 'from-rose-600 via-fuchsia-600 to-ultramarine-600', icon: ShieldAlert },
}
const FILTERS: [Kind | 'all', string][] = [
  ['all', 'All runs'],
  ['feature', 'Features'],
  ['bug', 'Bug fixes'],
  ['security', 'Security'],
]

/** The latest finished run of each task, newest first. */
function pickRuns(runs: RunSummary[], tasks: Task[]) {
  const seen = new Set<string>()
  const picked: { run: RunSummary; task?: Task }[] = []
  for (const run of runs) {
    if (run.status === 'running') continue
    const task = taskFor(run.task, tasks)
    const key = task?.id ?? run.task
    if (seen.has(key)) continue
    seen.add(key)
    picked.push({ run, task })
  }
  return picked
}

export function Gallery({
  runs,
  tasks,
  onOpen,
}: {
  runs: RunSummary[]
  tasks: Task[]
  onOpen: (id: string, mode: 'watch' | 'story') => void
}) {
  const [filter, setFilter] = useState<Kind | 'all'>('all')
  const all = pickRuns(runs, tasks)
  const shown = all.filter((r) => filter === 'all' || r.task?.kind === filter)
  const live = runs.filter((r) => r.status === 'running')

  return (
    <section id="runs" className="relative px-4 py-20 md:px-8">
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-1/2 bg-linear-to-b from-ultramarine-500/5 to-transparent dark:from-ultramarine-500/10" />
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <h2 className="text-4xl text-ink md:text-5xl">Recorded runs</h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted">
            Real runs on benchmark tasks the agents had never seen. Watch one play back, or read it
            as a case study.
          </p>
        </div>

        <div className="mt-10 flex flex-wrap justify-center gap-2">
          {FILTERS.map(([kind, label]) => (
            <button
              key={kind}
              type="button"
              onClick={() => setFilter(kind)}
              className={cx(
                'rounded-full px-4 py-2 text-sm font-medium transition-all duration-300',
                filter === kind
                  ? 'bg-ultramarine-600 text-white shadow-lg shadow-ultramarine-600/25'
                  : 'border border-line text-muted hover:border-ultramarine-500/40 hover:text-ink',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {live.length > 0 && (
          <div className="mx-auto mt-8 flex max-w-xl flex-col gap-2">
            {live.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => onOpen(r.id, 'watch')}
                className="flex items-center gap-3 rounded-full border border-ultramarine-500/40 bg-ultramarine-500/10 px-4 py-2 text-left text-sm text-body hover:bg-ultramarine-500/15"
              >
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ultramarine-400 opacity-70" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-ultramarine-400" />
                </span>
                <span className="font-medium text-ink">Live now:</span>
                <span className="truncate">{titleFor(r.task, tasks)}</span>
              </button>
            ))}
          </div>
        )}

        {shown.length === 0 ? (
          <p className="mt-16 text-center text-muted">No recorded runs here yet.</p>
        ) : (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map(({ run, task }, i) => (
              <RunCard key={run.id} run={run} task={task} index={i} onOpen={onOpen} />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function RunCard({
  run,
  task,
  index,
  onOpen,
}: {
  run: RunSummary
  task?: Task
  index: number
  onOpen: (id: string, mode: 'watch' | 'story') => void
}) {
  const style = KIND_STYLE[task?.kind ?? 'feature']
  const Icon = style.icon
  const passed = run.status === 'passed'
  const seconds = run.finished_at
    ? (new Date(run.finished_at).getTime() - new Date(run.created_at).getTime()) / 1000
    : null
  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.45, delay: (index % 3) * 0.08 }}
      className="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-line bg-card shadow-lg shadow-slate-200/50 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-ultramarine-500/40 hover:shadow-xl dark:shadow-black/20"
      onClick={() => onOpen(run.id, 'watch')}
    >
      <div
        className={cx(
          'relative flex h-40 items-center justify-center overflow-hidden bg-linear-to-br',
          style.gradient,
        )}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[18px_18px] opacity-60" />
        <div className="absolute -right-6 -bottom-8 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
        <Icon
          className="relative h-14 w-14 text-white/90 transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3"
          strokeWidth={1.4}
        />
        <span className="absolute top-3 left-3 rounded-full bg-black/25 px-3 py-1 text-[11px] font-medium text-white backdrop-blur-sm">
          {task ? KIND_LABEL[task.kind] : 'Run'}
        </span>
        <span
          className={cx(
            'absolute top-3 right-3 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold backdrop-blur-sm',
            passed ? 'bg-emerald-500/90 text-white' : 'bg-black/35 text-white',
          )}
        >
          {passed ? <CircleCheck className="h-3.5 w-3.5" /> : <CircleX className="h-3.5 w-3.5" />}
          {passed ? 'Passed' : 'Failed'}
        </span>
      </div>
      <div className="flex flex-1 flex-col p-5">
        <h3 className="text-xl text-ink transition-colors group-hover:text-accent">
          {task ? humanize(task.id) : titleFor(run.task, [])}
        </h3>
        <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">
          <Prose text={firstSentence(run.task)} />
        </p>
        <div className="mt-auto flex items-center justify-between gap-2 pt-5">
          <span className="text-xs text-faint">
            {usd(run.spent_usd, 4)}
            {seconds ? ` · ${formatDuration(seconds)}` : ''} · {timeAgo(run.created_at)}
          </span>
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onOpen(run.id, 'story')
              }}
              className="pill-outline h-8 w-8 p-0"
              aria-label="Read as a story"
              title="Read as a story"
            >
              <BookOpen className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onOpen(run.id, 'watch')
              }}
              className="pill-primary h-8 px-3 text-xs"
            >
              <Play className="h-3.5 w-3.5" /> Watch
            </button>
          </div>
        </div>
      </div>
    </motion.article>
  )
}
