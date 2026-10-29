import { useState } from 'react'
import type { PublicConfig, RunSummary, Task } from '../lib/types'
import { KIND_TONE, STATUS_TONE, cx, timeAgo, usd } from '../lib/format'
import { Badge, Panel } from './ui'

interface Props {
  config: PublicConfig | null
  tasks: Task[]
  runs: RunSummary[]
  selectedRun: string | null
  onStart: (taskId: string) => Promise<void>
  onSelectRun: (runId: string) => void
  startError: string | null
}

export function Sidebar({
  config,
  tasks,
  runs,
  selectedRun,
  onStart,
  onSelectRun,
  startError,
}: Props) {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const chosen = tasks.find((t) => t.id === taskId)

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
    <aside className="flex min-h-0 flex-col gap-4">
      <Panel title="Start a run">
        {config && !config.live_runs ? (
          <p className="p-4 text-sm leading-relaxed text-muted">
            This demo shows recorded runs of real models. Pick one below to replay it, or run
            AgentCollab yourself from the{' '}
            <a
              className="text-accent hover:underline"
              href="https://github.com/altesse-imena/AgentCollab"
            >
              GitHub repo
            </a>
            .
          </p>
        ) : (
          <div className="space-y-3 p-4">
            <label className="block text-xs text-muted" htmlFor="task">
              Benchmark task
            </label>
            <select
              id="task"
              value={taskId ?? ''}
              onChange={(e) => setTaskId(e.target.value || null)}
              className="w-full rounded-lg border border-line-strong bg-sunken px-3 py-2 text-sm focus:border-ultramarine-500 focus:outline-none"
            >
              <option value="">Choose a task…</option>
              {(['feature', 'bug', 'security'] as const).map((kind) => (
                <optgroup key={kind} label={kind[0].toUpperCase() + kind.slice(1)}>
                  {tasks
                    .filter((t) => t.kind === kind)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.id.replaceAll('_', ' ')}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            {chosen && (
              <p className="rounded-lg bg-sunken p-3 text-xs leading-relaxed text-muted">
                <Badge tone={KIND_TONE[chosen.kind]}>{chosen.kind}</Badge> {chosen.prompt}
              </p>
            )}
            <button
              type="button"
              onClick={start}
              disabled={!taskId || starting}
              className="pill-primary w-full px-4 py-2.5 text-sm"
            >
              {starting ? 'Starting…' : 'Run agents'}
            </button>
            {startError && <p className="text-xs text-bad">{startError}</p>}
            {config?.runs_per_day && (
              <p className="text-[11px] text-faint">
                Up to {config.runs_per_day} runs per day, each capped at{' '}
                {usd(config.run_budget_usd, 2)}.
              </p>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Recent runs" className="flex min-h-0 flex-1 flex-col">
        <ul className="min-h-0 flex-1 divide-y divide-line overflow-y-auto">
          {runs.length === 0 && <li className="p-4 text-xs text-faint">No runs yet.</li>}
          {runs.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => onSelectRun(r.id)}
                className={cx(
                  'w-full px-4 py-3 text-left transition hover:bg-hover',
                  r.id === selectedRun && 'bg-ultramarine-500/10',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                  <span className="text-[11px] text-faint">
                    {usd(r.spent_usd)} · {timeAgo(r.created_at)}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-xs text-muted">{r.task}</p>
              </button>
            </li>
          ))}
        </ul>
      </Panel>
    </aside>
  )
}
