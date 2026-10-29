import { useRunEvents } from '../lib/api'
import { AgentGraph } from './AgentGraph'
import { RoundDetails } from './RoundDetails'
import { StatsBar } from './StatsBar'
import { Timeline } from './Timeline'
import { Panel } from './ui'

export function RunView({ runId, speed }: { runId: string; speed: number }) {
  const { view, connected } = useRunEvents(runId, speed)
  return (
    <div className="flex min-h-0 flex-col gap-4">
      <Panel>
        {view.task && (
          <p className="border-b border-slate-800 px-4 py-3 text-sm text-slate-300">{view.task}</p>
        )}
        <StatsBar view={view} connected={connected} />
      </Panel>
      <Panel title="Agents">
        <AgentGraph view={view} />
      </Panel>
      <div className="grid min-h-0 gap-4 xl:grid-cols-[380px_1fr]">
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
