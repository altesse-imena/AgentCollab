import { useCallback, useEffect, useState } from 'react'
import { GithubIcon } from 'lucide-react'
import { RunView } from './components/RunView'
import { Sidebar } from './components/Sidebar'
import { ThemeToggle } from './components/ThemeToggle'
import { Welcome } from './components/Welcome'
import { api } from './lib/api'
import type { PublicConfig, RunSummary, Task } from './lib/types'

// #/runs/<id> opens a run; #/runs/<id>/replay/<speed> replays it (shareable demo links)
function routeFromHash(): { runId: string | null; speed: number } {
  const match = location.hash.match(/^#\/runs\/([\w-]+)(?:\/replay\/(\d+))?/)
  return { runId: match?.[1] ?? null, speed: Number(match?.[2] ?? 0) }
}

export default function App() {
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [route, setRoute] = useState(routeFromHash)
  const [startError, setStartError] = useState<string | null>(null)

  const refreshRuns = useCallback(
    () =>
      api
        .runs()
        .then(setRuns)
        .catch(() => {}),
    [],
  )

  useEffect(() => {
    api
      .config()
      .then(setConfig)
      .catch(() => {})
    api
      .tasks()
      .then(setTasks)
      .catch(() => {})
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
    <div className="relative isolate flex h-full flex-col">
      {/* Soft ultramarine wash behind the top of the page, as on the portfolio */}
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[520px] bg-linear-to-b from-ultramarine-500/5 to-transparent dark:from-ultramarine-500/10" />
      <header className="sticky top-0 z-50 border-b border-line bg-canvas/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3">
          <a href="#/" className="flex min-w-0 items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-8 w-8" />
            <div className="min-w-0">
              <h1 className="text-xl leading-tight font-medium">
                <span className="gradient-text">AgentCollab</span>
              </h1>
              <p className="hidden truncate text-xs text-muted sm:block">
                Four AI agents write, review, test and secure code together
              </p>
            </div>
          </a>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href="https://github.com/altesse-imena/AgentCollab"
              target="_blank"
              rel="noopener noreferrer"
              className="pill-outline px-3 py-2 text-sm"
              aria-label="Source code on GitHub"
            >
              <GithubIcon className="h-4 w-4" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <div className="mx-auto grid min-h-0 w-full max-w-[1600px] flex-1 grid-cols-1 gap-4 p-4 *:min-w-0 lg:grid-cols-[320px_1fr]">
        <Sidebar
          config={config}
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
