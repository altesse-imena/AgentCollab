import { ArrowRightIcon } from 'lucide-react'
import type { RunSummary } from '../lib/types'
import { Panel } from './ui'

const STEPS = [
  ['CodeWriter', 'reads the repo and proposes a change'],
  ['Reviewer, TestGenerator, SecurityAnalyzer', 'inspect that change in parallel'],
  ['TestRunner', 'runs the tests in an isolated Docker sandbox with no network'],
  ['Judge', 'passes the round, or sends every failure back to CodeWriter'],
]

export function Welcome({
  runs,
  onReplay,
}: {
  runs: RunSummary[]
  onReplay: (id: string) => void
}) {
  const featured = runs.find((r) => r.status === 'passed')
  return (
    <Panel className="p-8 md:p-10">
      <h2 className="text-3xl text-ink md:text-4xl">
        Watch AI agents <span className="gradient-text">collaborate on code</span>
      </h2>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted md:text-lg">
        Pick a benchmark task, or replay a recorded run. Each run is orchestrated with LangGraph,
        and every model call is tracked for cost.
      </p>
      <ol className="mt-8 grid gap-3 md:grid-cols-2">
        {STEPS.map(([who, what], i) => (
          <li
            key={who}
            className="flex gap-3 rounded-xl border border-line bg-sunken/50 p-4 transition-colors duration-300 hover:border-ultramarine-500/30"
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ultramarine-600 text-xs font-semibold text-white">
              {i + 1}
            </span>
            <p className="text-sm leading-relaxed text-body">
              <span className="font-medium text-ink">{who}</span> {what}
            </p>
          </li>
        ))}
      </ol>
      {featured && (
        <button
          type="button"
          onClick={() => onReplay(featured.id)}
          className="pill-primary group mt-8 px-6 py-3 text-sm"
        >
          Replay a recorded run
          <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </button>
      )}
    </Panel>
  )
}
