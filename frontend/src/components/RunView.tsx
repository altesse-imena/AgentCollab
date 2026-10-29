import { useState } from 'react'
import { useRunEvents } from '../lib/api'
import { cx } from '../lib/format'
import { AgentGraph } from './AgentGraph'
import { RoundDetails } from './RoundDetails'
import { StatsBar } from './StatsBar'
import { Timeline } from './Timeline'
import { Panel } from './ui'

const SPEEDS = [1, 4, 16]

export function RunView({ runId, initialSpeed = 0 }: { runId: string; initialSpeed?: number }) {
  const [speed, setSpeed] = useState(initialSpeed)
  const [nonce, setNonce] = useState(0)
  const { view, connected } = useRunEvents(runId, speed, nonce)
  const finished = !['waiting', 'running'].includes(view.status)
  const replaying = speed > 0 && !finished

  const replay = (s: number) => {
    setSpeed(s)
    setNonce((n) => n + 1)
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 px-4 py-3">
          <p className="min-w-0 flex-1 text-sm text-slate-300">{view.task ?? 'Loading…'}</p>
          {(finished || replaying) && (
            <div className="flex items-center gap-1 text-xs">
              <span className="mr-1 text-slate-500">{replaying ? 'Replaying' : 'Replay'}</span>
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => replay(s)}
                  className={cx(
                    'rounded-md px-2 py-1 font-medium',
                    replaying && speed === s
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700',
                  )}
                >
                  {s}×
                </button>
              ))}
            </div>
          )}
        </div>
        <StatsBar view={view} connected={connected} replaying={replaying} />
      </Panel>
      <Panel title="Agents">
        <AgentGraph view={view} />
      </Panel>
      <div className="grid min-h-0 gap-4 *:min-w-0 xl:grid-cols-[380px_1fr]">
        <Panel title="Timeline" className="flex max-h-[560px] min-h-0 flex-col">
          <div className="min-h-0 flex-1">
            <Timeline items={view.timeline} />
          </div>
        </Panel>
        <Panel title="Results" className="flex max-h-[560px] min-h-[320px] flex-col">
          <RoundDetails rounds={view.rounds} />
        </Panel>
      </div>
    </div>
  )
}
