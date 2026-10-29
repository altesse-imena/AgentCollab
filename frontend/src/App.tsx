import { useCallback, useEffect, useState } from 'react'
import { RunView } from './components/RunView'
import { Sidebar } from './components/Sidebar'
import { api } from './lib/api'
import type { RunSummary, Task } from './lib/types'

function runIdFromHash(): string | null {
  const match = location.hash.match(/^#\/runs\/([\w-]+)/)
  return match ? match[1] : null
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [runId, setRunId] = useState<string | null>(runIdFromHash)
  const [startError, setStartError] = useState<string | null>(null)

  const refreshRuns = useCallback(() => api.runs().then(setRuns).catch(() => {}), [])

  useEffect(() => {
    api.tasks().then(setTasks).catch(() => {})
    refreshRuns()
    const timer = setInterval(refreshRuns, 5000)
    const onHash = () => setRunId(runIdFromHash())
    window.addEventListener('hashchange', onHash)
    return () => {
      clearInterval(timer)
      window.removeEventListener('hashchange', onHash)
    }
  }, [refreshRuns])

  const selectRun = (id: string) => {
    location.hash = `#/runs/${id}`
  }

  const start = async (taskId: string) => {
    setStartError(null)
    try {
      const { run_id } = await api.start(taskId)
      selectRun(run_id)
      refreshRuns()
    } catch (e) {
      setStartError((e as Error).message)
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-[1600px] flex-col gap-4 p-4">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-8 w-8" />
          <div>
            <h1 className="text-lg font-semibold text-white">AgentCollab</h1>
            <p className="text-xs text-slate-400">
              Four AI agents write, review, test and secure code together
            </p>
          </div>
        </div>
        <a
          href="https://github.com/altesse-imena/AgentCollab"
          className="text-xs text-slate-400 hover:text-white"
        >
          GitHub →
        </a>
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <Sidebar
          tasks={tasks}
          runs={runs}
          selectedRun={runId}
          onStart={start}
          onSelectRun={selectRun}
          startError={startError}
        />
        <main className="min-h-0">
          {runId ? (
            <RunView runId={runId} speed={0} />
          ) : (
            <p className="text-sm text-slate-400">Pick a task to watch the agents work.</p>
          )}
        </main>
      </div>
    </div>
  )
}
