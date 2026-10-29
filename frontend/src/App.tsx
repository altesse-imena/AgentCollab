import { useCallback, useEffect, useState } from 'react'
import { RunView } from './components/RunView'
import { Sidebar } from './components/Sidebar'
import { Welcome } from './components/Welcome'
import { api } from './lib/api'
import type { RunSummary, Task } from './lib/types'

// #/runs/<id> opens a run; #/runs/<id>/replay/<speed> replays it (shareable demo links)
function routeFromHash(): { runId: string | null; speed: number } {
  const match = location.hash.match(/^#\/runs\/([\w-]+)(?:\/replay\/(\d+))?/)
  return { runId: match?.[1] ?? null, speed: Number(match?.[2] ?? 0) }
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [route, setRoute] = useState(routeFromHash)
  const [startError, setStartError] = useState<string | null>(null)

  const refreshRuns = useCallback(() => api.runs().then(setRuns).catch(() => {}), [])

  useEffect(() => {
    api.tasks().then(setTasks).catch(() => {})
    refreshRuns()
    const timer = setInterval(refreshRuns, 5000)
    const onHash = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHash)
    return () => {
      clearInterval(timer)
      window.removeEventListener('hashchange', onHash)
    }
  }, [refreshRuns])

  const selectRun = (id: string, speed = 0) => {
    location.hash = speed ? `#/runs/${id}/replay/${speed}` : `#/runs/${id}`
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
        <a href="#/" className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-8 w-8" />
          <div>
            <h1 className="text-lg font-semibold text-white">AgentCollab</h1>
            <p className="text-xs text-slate-400">
              Four AI agents write, review, test and secure code together
            </p>
          </div>
        </a>
        <a
          href="https://github.com/altesse-imena/AgentCollab"
          className="text-xs text-slate-400 hover:text-white"
        >
          GitHub →
        </a>
      </header>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 *:min-w-0 lg:grid-cols-[320px_1fr]">
        <Sidebar
          tasks={tasks}
          runs={runs}
          selectedRun={route.runId}
          onStart={start}
          onSelectRun={(id) => selectRun(id)}
          startError={startError}
        />
        <main className={route.runId ? 'order-first min-h-0 lg:order-none' : 'min-h-0'}>
          {route.runId ? (
            <RunView
              key={`${route.runId}-${route.speed}`}
              runId={route.runId}
              initialSpeed={route.speed}
            />
          ) : (
            <Welcome runs={runs} onReplay={(id) => selectRun(id, 4)} />
          )}
        </main>
      </div>
    </div>
  )
}
