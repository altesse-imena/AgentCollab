import { useRunEvents } from '../lib/api'
import { AgentGraph } from './AgentGraph'
import { StatsBar } from './StatsBar'
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
    </div>
  )
}
