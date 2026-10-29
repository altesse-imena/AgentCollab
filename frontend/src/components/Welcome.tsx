import type { RunSummary } from '../lib/types'
import { Panel } from './ui'

const STEPS = [
  ['CodeWriter', 'reads the repo and proposes a change'],
  ['Reviewer, TestGenerator, SecurityAnalyzer', 'inspect that change in parallel'],
  ['TestRunner', 'runs the tests in an isolated Docker sandbox with no network'],
  ['Judge', 'passes the round, or sends every failure back to CodeWriter'],
]

export function Welcome({ runs, onReplay }: { runs: RunSummary[]; onReplay: (id: string) => void }) {
  const featured = runs.find((r) => r.status === 'passed')
  return (
    <Panel className="p-8">
      <h2 className="text-xl font-semibold text-white">Watch AI agents collaborate on code</h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
        Pick a benchmark task on the left, or replay a recorded run. Each run is orchestrated
        with LangGraph, and every model call is tracked for cost.
      </p>
      <ol className="mt-6 grid gap-3 md:grid-cols-2">
        {STEPS.map(([who, what], i) => (
          <li key={who} className="flex gap-3 rounded-lg border border-slate-800 p-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
              {i + 1}
            </span>
            <p className="text-sm text-slate-300">
              <span className="font-medium text-white">{who}</span> {what}
            </p>
          </li>
        ))}
      </ol>
      {featured && (
        <button
          type="button"
          onClick={() => onReplay(featured.id)}
          className="mt-6 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
        >
          ▶ Replay a recorded run
        </button>
      )}
    </Panel>
  )
}
