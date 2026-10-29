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
          <p className="p-4 text-sm leading-relaxed text-slate-400">
            This demo shows recorded runs of real models. Pick one below to replay it, or run
            AgentCollab yourself from the{' '}
            <a
              className="text-brand-300 hover:underline"
              href="https://github.com/altesse-imena/AgentCollab"
            >
              GitHub repo
            </a>
            .
          </p>
        ) : (
          <div className="space-y-3 p-4">
            <label className="block text-xs text-slate-400" htmlFor="task">
              Benchmark task
            </label>
            <select
              id="task"
              value={taskId ?? ''}
              onChange={(e) => setTaskId(e.target.value || null)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
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
              <p className="rounded-lg bg-slate-950/70 p-3 text-xs leading-relaxed text-slate-400">
                <Badge tone={KIND_TONE[chosen.kind]}>{chosen.kind}</Badge> {chosen.prompt}
              </p>
            )}
            <button
              type="button"
              onClick={start}
              disabled={!taskId || starting}
              className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {starting ? 'Starting…' : 'Run agents'}
            </button>
            {startError && <p className="text-xs text-rose-300">{startError}</p>}
            {config?.runs_per_day && (
              <p className="text-[11px] text-slate-500">
                Up to {config.runs_per_day} runs per day, each capped at{' '}
                {usd(config.run_budget_usd, 2)}.
              </p>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Recent runs" className="flex min-h-0 flex-1 flex-col">
        <ul className="min-h-0 flex-1 divide-y divide-slate-800 overflow-y-auto">
          {runs.length === 0 && <li className="p-4 text-xs text-slate-500">No runs yet.</li>}
          {runs.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => onSelectRun(r.id)}
                className={cx(
                  'w-full px-4 py-3 text-left transition hover:bg-slate-800/60',
                  r.id === selectedRun && 'bg-brand-500/10',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                  <span className="text-[11px] text-slate-500">
                    {usd(r.spent_usd)} · {timeAgo(r.created_at)}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-xs text-slate-400">{r.task}</p>
              </button>
            </li>
          ))}
        </ul>
      </Panel>
    </aside>
  )
}
