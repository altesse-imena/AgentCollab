import { useEffect, useReducer, useRef, useState } from 'react'
import { applyEvent, initialView, type RunView } from './runState'
import type { PublicConfig, RunEvent, RunSummary, Task } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  config: () => request<PublicConfig>('/api/config'),
  tasks: () => request<Task[]>('/api/tasks'),
  runs: () => request<RunSummary[]>('/api/runs'),
  run: (id: string) => request<RunSummary>(`/api/runs/${id}`),
  start: (taskId: string, maxIterations = 3) =>
    request<{ run_id: string }>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId, max_iterations: maxIterations }),
    }),
}

type Action = { type: 'event'; event: RunEvent } | { type: 'reset' }

function reducer(view: RunView, action: Action): RunView {
  return action.type === 'reset' ? initialView() : applyEvent(view, action.event)
}

const TERMINAL = new Set(['run_finished', 'run_crashed'])

/**
 * Streams a run's events into a RunView. Reconnects from the last seen event if the
 * connection drops. speed > 0 replays a finished run at its original pace, sped up.
 */
export function useRunEvents(runId: string | null, speed: number, replayNonce = 0) {
  const [view, dispatch] = useReducer(reducer, undefined, initialView)
  const [connected, setConnected] = useState(false)
  const lastSeq = useRef(-1)

  useEffect(() => {
    dispatch({ type: 'reset' })
    lastSeq.current = -1
    if (!runId) return

    let ws: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let done = false
    let attempts = 0

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const params = new URLSearchParams({ after: String(lastSeq.current), speed: String(speed) })
      ws = new WebSocket(`${proto}://${location.host}/api/runs/${runId}/events?${params}`)
      ws.onopen = () => {
        attempts = 0
        setConnected(true)
      }
      ws.onmessage = (msg) => {
        const event = JSON.parse(msg.data) as RunEvent
        lastSeq.current = Math.max(lastSeq.current, event.seq)
        dispatch({ type: 'event', event })
        if (TERMINAL.has(event.type)) done = true
      }
      ws.onclose = () => {
        setConnected(false)
        if (!done) retry = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 10_000))
      }
    }
    connect()
    return () => {
      done = true
      clearTimeout(retry)
      ws?.close()
    }
  }, [runId, speed, replayNonce])

  return { view, connected }
}
