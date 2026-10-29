import { describe, expect, it } from 'vitest'
import { applyEvent, initialView, replay } from './runState'
import type { RunEvent } from './types'

let seq = 0
const ev = (type: RunEvent['type'], data: Record<string, any> = {}): RunEvent => ({
  seq: seq++,
  type,
  data,
  at: new Date(2026, 0, 1, 0, 0, seq).toISOString(),
})

function round(iteration: number, passed: boolean): RunEvent[] {
  return [
    ev('node_started', { node: 'write' }),
    ev('llm_call', {
      agent: 'code_writer',
      model: 'gpt-4.1',
      cost_usd: 0.01,
      prompt_tokens: 1000,
      cached_tokens: 200,
      completion_tokens: 300,
      latency_ms: 900,
      cache_hit: false,
    }),
    ev('node_finished', {
      node: 'write',
      iteration,
      summary: `attempt ${iteration}`,
      files: ['app.py'],
      patch: '+x',
    }),
    ev('node_started', { node: 'review' }),
    ev('node_started', { node: 'security' }),
    ev('node_finished', {
      node: 'review',
      output: passed
        ? { approved: true, comments: [] }
        : {
            approved: false,
            comments: [{ path: 'app.py', line: 1, severity: 'major', message: 'bug' }],
          },
    }),
    ev('node_finished', { node: 'security', error: 'invalid output twice' }),
    ev('node_finished', {
      node: 'run_tests',
      result: {
        passed,
        exit_code: passed ? 0 : 1,
        output: '',
        duration_ms: 1200,
        timed_out: false,
      },
    }),
    ev('node_finished', { node: 'judge', iteration, passed, tests_passed: passed }),
  ]
}

describe('applyEvent', () => {
  const events = [
    ev('run_started', { task: 'add greet', budget_usd: 0.5, max_iterations: 3 }),
    ev('node_finished', { node: 'gather_context', files: ['app.py', 'README.md'] }),
    ...round(1, false),
    ...round(2, true),
    ev('run_finished', { status: 'passed', spent_usd: 0.02, iterations: 2, error: null }),
  ]
  const view = replay(events)

  it('tracks status, rounds and cost', () => {
    expect(view.status).toBe('passed')
    expect(view.iteration).toBe(2)
    expect(view.rounds.map((r) => r.summary)).toEqual(['attempt 1', 'attempt 2'])
    expect(view.spentUsd).toBeCloseTo(0.02)
    expect(view.tokens).toEqual({ prompt: 2000, cached: 400, completion: 600 })
    expect(view.contextFiles).toHaveLength(2)
  })

  it('attaches agent results and errors to the right round', () => {
    expect(view.rounds[0].review?.approved).toBe(false)
    expect(view.rounds[0].agentErrors.security).toBe('invalid output twice')
    expect(view.rounds[1].testResult?.passed).toBe(true)
    expect(view.rounds[1].verdict?.passed).toBe(true)
  })

  it('marks failed agents and clears active nodes at the end', () => {
    expect(view.nodes.security).toBe('failed')
    expect(view.nodes.review).toBe('done')
    expect(view.activeNodes).toEqual([])
  })

  it('resets the round nodes when CodeWriter starts again', () => {
    const mid = replay(events.slice(0, 2 + round(1, false).length + 1))
    expect(mid.nodes.write).toBe('running')
    expect(mid.nodes.review).toBe('idle')
  })

  it('ignores duplicate events after a reconnect', () => {
    const again = applyEvent(view, events[3])
    expect(again).toBe(view)
  })

  it('handles crashes', () => {
    const crashed = applyEvent(initialView(), ev('run_crashed', { error: 'boom' }))
    expect(crashed.status).toBe('crashed')
    expect(crashed.timeline.at(-1)?.tone).toBe('bad')
  })
})
