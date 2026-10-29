import { STATUS_TONE, cx, usd } from '../lib/format'
import type { RunView } from '../lib/runState'
import { Badge } from './ui'

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-1 truncate text-sm font-medium text-white">{children}</div>
    </div>
  )
}

export function StatsBar({
  view,
  connected,
  replaying = false,
}: {
  view: RunView
  connected: boolean
  replaying?: boolean
}) {
  const budgetUsed = view.budgetUsd ? Math.min(1, view.spentUsd / view.budgetUsd) : 0
  const cacheRate = view.tokens.prompt ? view.tokens.cached / view.tokens.prompt : 0
  return (
    <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 xl:grid-cols-6">
      <Stat label="Status">
        <div className="flex items-center gap-2">
          <Badge tone={STATUS_TONE[view.status]}>{view.status}</Badge>
          {view.status === 'running' && (
            <span className={cx('text-[11px]', connected ? 'text-slate-500' : 'text-amber-300')}>
              {!connected ? 'reconnecting…' : replaying ? 'replay' : 'live'}
            </span>
          )}
        </div>
      </Stat>
      <Stat label="Round">
        {view.iteration || '–'} <span className="text-slate-500">/ {view.maxIterations}</span>
      </Stat>
      <Stat label="Cost">
        <div className="flex items-center gap-2">
          <span>{usd(view.spentUsd)}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800" title="of budget">
            <div
              className={cx(
                'h-full rounded-full transition-all',
                budgetUsed > 0.85 ? 'bg-rose-400' : 'bg-brand-400',
              )}
              style={{ width: `${budgetUsed * 100}%` }}
            />
          </div>
        </div>
        <p className="text-[11px] font-normal text-slate-500">of {usd(view.budgetUsd, 2)} budget</p>
      </Stat>
      <Stat label="Model calls">{view.calls.length}</Stat>
      <Stat label="Tokens">
        {(view.tokens.prompt + view.tokens.completion).toLocaleString()}
      </Stat>
      <Stat label="Prompt cache">{Math.round(cacheRate * 100)}% reused</Stat>
    </div>
  )
}
