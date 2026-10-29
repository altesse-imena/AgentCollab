import { Github, Play } from 'lucide-react'
import { useState } from 'react'
import { usd } from '../../lib/format'
import { humanize, KIND_LABEL } from '../../lib/story'
import type { PublicConfig, Task } from '../../lib/types'
import { Prose } from '../Prose'

/** Start a live run, when the server allows it; otherwise point to running it yourself. */
export function TryIt({
  config,
  tasks,
  onStart,
  error,
}: {
  config: PublicConfig | null
  tasks: Task[]
  onStart: (taskId: string) => Promise<void>
  error: string | null
}) {
  const [taskId, setTaskId] = useState('')
  const [starting, setStarting] = useState(false)
  const chosen = tasks.find((t) => t.id === taskId)
  const live = config?.live_runs

  const start = async () => {
    if (!taskId) return
    setStarting(true)
    try {
      await onStart(taskId)
    } finally {
      setStarting(false)
    }
  }

  return (
    <section className="px-4 pb-24 md:px-8">
      <div className="relative mx-auto max-w-4xl overflow-hidden rounded-3xl border border-line bg-card p-8 text-center backdrop-blur-sm md:p-12">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(57,255,20,0.16),transparent_60%)]" />
        <h2 className="relative text-3xl text-ink md:text-4xl">
          {live ? 'Give the agents a task' : 'Run it on your own machine'}
        </h2>
        <p className="relative mx-auto mt-3 max-w-xl text-muted">
          {live
            ? 'Pick a benchmark task and watch the agents work on it live.'
            : 'This public demo replays recorded runs. Clone the repo, add a model key, and the same agents will work on your own code.'}
        </p>
        {live ? (
          <div className="relative mx-auto mt-8 flex max-w-xl flex-col gap-3 sm:flex-row">
            <select
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              aria-label="Benchmark task"
              className="flex-1 rounded-full border border-line-strong bg-sunken px-5 py-3 text-sm text-body focus:border-brand-500 focus:outline-none"
            >
              <option value="">Choose a task…</option>
              {(['feature', 'bug', 'security'] as const).map((kind) => (
                <optgroup key={kind} label={KIND_LABEL[kind]}>
                  {tasks
                    .filter((t) => t.kind === kind)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {humanize(t.id)}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            <button
              type="button"
              onClick={start}
              disabled={!taskId || starting}
              className="pill-primary px-6 py-3 text-sm"
            >
              <Play className="h-4 w-4" />
              {starting ? 'Starting…' : 'Run the agents'}
            </button>
          </div>
        ) : (
          <a
            href="https://github.com/altesse-imena/AgentCollab"
            target="_blank"
            rel="noopener noreferrer"
            className="pill-primary relative mt-8 px-6 py-3 text-sm"
          >
            <Github className="h-4 w-4" /> Get the code
          </a>
        )}
        {chosen && (
          <p className="relative mx-auto mt-5 max-w-xl text-left text-sm leading-relaxed text-muted">
            <Prose text={chosen.prompt} />
          </p>
        )}
        {error && <p className="relative mt-4 text-sm text-bad">{error}</p>}
        {live && config?.runs_per_day && (
          <p className="relative mt-4 text-xs text-faint">
            Up to {config.runs_per_day} runs per visitor per day, each capped at{' '}
            {usd(config.run_budget_usd, 2)}.
          </p>
        )}
      </div>
    </section>
  )
}
