import { GithubIcon } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Gallery } from './components/home/Gallery'
import { Hero } from './components/home/Hero'
import { TryIt } from './components/home/TryIt'
import { type RunMode, RunPage } from './components/run/RunPage'
import { ThemeToggle } from './components/ThemeToggle'
import { api } from './lib/api'
import { showcaseStats, taskFor } from './lib/story'
import type { PublicConfig, RunSummary, Task } from './lib/types'

// #/runs/<id> watches a run, #/runs/<id>/story reads it as a case study.
// #/runs/<id>/replay/<speed> (older shared links) replays at a fixed speed.
interface Route {
  runId: string | null
  mode: RunMode
  speed: number | null
}
function routeFromHash(): Route {
  const m = location.hash.match(/^#\/runs\/([\w-]+)(?:\/(story|watch|replay)(?:\/(\d+))?)?/)
  if (!m) return { runId: null, mode: 'watch', speed: null }
  return {
    runId: m[1],
    mode: m[2] === 'story' ? 'story' : 'watch',
    speed: m[3] !== undefined ? Number(m[3]) : null,
  }
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
    const onHash = () => {
      setRoute(routeFromHash())
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', onHash)
    return () => {
      clearInterval(timer)
      window.removeEventListener('hashchange', onHash)
    }
  }, [refreshRuns])

  const open = (id: string, mode: RunMode = 'watch') => {
    location.hash = mode === 'story' ? `#/runs/${id}/story` : `#/runs/${id}`
  }

  const start = async (taskId: string) => {
    setStartError(null)
    try {
      const { run_id } = await api.start(taskId)
      open(run_id)
      refreshRuns()
    } catch (e) {
      setStartError((e as Error).message)
    }
  }

  // The hero's buttons open a passing run, a security fix if there is one
  const featured = useMemo(() => {
    const passed = runs.filter((r) => r.status === 'passed')
    return passed.find((r) => taskFor(r.task, tasks)?.kind === 'security') ?? passed[0]
  }, [runs, tasks])

  return (
    <div className="relative isolate flex min-h-full flex-col">
      <header className="sticky top-0 z-50 border-b border-line bg-canvas/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 md:px-8">
          <a href="#/" className="flex min-w-0 items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-8 w-8" />
            <span className="font-heading text-xl font-medium">
              <span className="gradient-text">AgentCollab</span>
            </span>
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

      <main className="flex-1">
        {route.runId ? (
          <RunPage
            key={`${route.runId}-${route.mode}-${route.speed}`}
            runId={route.runId}
            mode={route.mode}
            initialSpeed={route.speed}
            tasks={tasks}
            onMode={(mode) => open(route.runId!, mode)}
          />
        ) : (
          <>
            <Hero
              stats={showcaseStats(runs)}
              onWatch={featured ? () => open(featured.id) : undefined}
              onStory={featured ? () => open(featured.id, 'story') : undefined}
            />
            <Gallery runs={runs} tasks={tasks} onOpen={open} />
            <TryIt config={config} tasks={tasks} onStart={start} error={startError} />
          </>
        )}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-8 text-sm text-faint sm:flex-row md:px-8">
          <p>
            Built by{' '}
            <a href="https://altesseimena.com" className="text-muted hover:text-ink">
              Altesse Imena
            </a>
          </p>
          <p>LangGraph · FastAPI · React · Docker sandbox</p>
        </div>
      </footer>
    </div>
  )
}
