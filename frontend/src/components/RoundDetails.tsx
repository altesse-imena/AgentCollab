import { useState } from 'react'
import { cx } from '../lib/format'
import type { Round } from '../lib/runState'
import type { Finding, ReviewComment } from '../lib/types'
import { DiffView } from './DiffView'
import { Badge } from './ui'

const TABS = ['Changes', 'Review', 'Security', 'Tests'] as const
type Tab = (typeof TABS)[number]

const SEVERITY_TONE = {
  blocker: 'bad',
  major: 'bad',
  critical: 'bad',
  high: 'bad',
  minor: 'warn',
  medium: 'warn',
  nit: 'neutral',
  low: 'neutral',
} as const

function where(path: string, line: number | null) {
  return (
    <span className="font-mono text-xs text-slate-400">
      {path}
      {line ? `:${line}` : ''}
    </span>
  )
}

function AgentError({ message }: { message?: string }) {
  return message ? (
    <p className="m-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
      This agent failed this round, so the judge worked without it: {message}
    </p>
  ) : null
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="p-4 text-sm text-slate-500">{children}</p>
}

export function RoundDetails({ rounds }: { rounds: Round[] }) {
  const [tab, setTab] = useState<Tab>('Changes')
  // null follows the newest round as it arrives; a number pins the one the user picked
  const [picked, setIndex] = useState<number | null>(null)
  const index = picked ?? rounds.length - 1

  const round = rounds[index]
  if (!round) return <Empty>CodeWriter hasn't proposed a change yet.</Empty>

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-3 py-2">
        {rounds.length > 1 &&
          rounds.map((r, i) => (
            <button
              key={r.iteration}
              type="button"
              onClick={() => setIndex(i)}
              className={cx(
                'rounded-md px-2 py-1 text-xs',
                i === index ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white',
              )}
            >
              Round {r.iteration}
            </button>
          ))}
        <div className="ml-auto flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={cx(
                'rounded-md px-2.5 py-1 text-xs font-medium',
                t === tab ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white',
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === 'Changes' && (
          <>
            {round.summary && <p className="px-4 pt-4 text-sm text-slate-300">{round.summary}</p>}
            <DiffView patch={round.patch} />
          </>
        )}

        {tab === 'Review' && (
          <>
            <AgentError message={round.agentErrors.review} />
            {!round.review ? (
              !round.agentErrors.review && <Empty>Review in progress…</Empty>
            ) : (
              <div className="space-y-2 p-4">
                <Badge tone={round.review.approved ? 'good' : 'warn'}>
                  {round.review.approved ? 'Approved' : 'Changes requested'}
                </Badge>
                {round.review.comments.length === 0 && (
                  <p className="text-sm text-slate-500">No comments.</p>
                )}
                {round.review.comments.map((c: ReviewComment, i) => (
                  <div key={i} className="rounded-lg border border-slate-800 p-3">
                    <div className="flex items-center gap-2">
                      <Badge tone={SEVERITY_TONE[c.severity]}>{c.severity}</Badge>
                      {where(c.path, c.line)}
                    </div>
                    <p className="mt-1.5 text-sm text-slate-300">{c.message}</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {tab === 'Security' && (
          <>
            <AgentError message={round.agentErrors.security} />
            {!round.security ? (
              !round.agentErrors.security && <Empty>Security analysis in progress…</Empty>
            ) : round.security.findings.length === 0 ? (
              <Empty>No security issues found.</Empty>
            ) : (
              <div className="space-y-2 p-4">
                {round.security.findings.map((f: Finding, i) => (
                  <div key={i} className="rounded-lg border border-slate-800 p-3">
                    <div className="flex items-center gap-2">
                      <Badge tone={SEVERITY_TONE[f.severity]}>{f.severity}</Badge>
                      {f.cwe && <Badge>{f.cwe}</Badge>}
                      {where(f.path, f.line)}
                    </div>
                    <p className="mt-1.5 text-sm text-slate-300">{f.issue}</p>
                    <p className="mt-1 text-xs text-slate-400">Fix: {f.fix}</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {tab === 'Tests' && (
          <>
            <AgentError message={round.agentErrors.tests} />
            {round.testResult && (
              <div className="p-4 pb-0">
                <div className="flex items-center gap-2">
                  <Badge tone={round.testResult.passed ? 'good' : 'bad'}>
                    {round.testResult.passed
                      ? 'passed'
                      : round.testResult.timed_out
                        ? 'timed out'
                        : 'failed'}
                  </Badge>
                  <span className="text-xs text-slate-500">
                    sandbox run · {(round.testResult.duration_ms / 1000).toFixed(1)}s
                  </span>
                </div>
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] leading-5 text-slate-400">
                  {round.testResult.output.trim()}
                </pre>
              </div>
            )}
            {round.tests?.files.map((f) => (
              <div key={f.path} className="p-4 pb-0 last:pb-4">
                <p className="mb-1 font-mono text-xs text-slate-400">{f.path}</p>
                <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 font-mono text-[12px] leading-5 text-slate-300">
                  {f.content}
                </pre>
              </div>
            ))}
            {!round.tests && !round.testResult && !round.agentErrors.tests && (
              <Empty>Tests are being written…</Empty>
            )}
          </>
        )}
      </div>
    </div>
  )
}
