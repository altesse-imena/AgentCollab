import type { FileEdit, Finding, ReviewComment, RunEvent, TestResult } from './types'

export const NODES = [
  'gather_context',
  'write',
  'review',
  'tests',
  'security',
  'run_tests',
  'judge',
  'finalize',
] as const
export type NodeId = (typeof NODES)[number]
export type NodeStatus = 'idle' | 'running' | 'done' | 'failed'

export const NODE_LABELS: Record<NodeId, string> = {
  gather_context: 'ContextGatherer',
  write: 'CodeWriter',
  review: 'CodeReviewer',
  tests: 'TestGenerator',
  security: 'SecurityAnalyzer',
  run_tests: 'TestRunner',
  judge: 'Judge',
  finalize: 'Finalize',
}

// Steps that run again in every round
const ROUND_NODES: NodeId[] = ['review', 'tests', 'security', 'run_tests', 'judge']

const AGENT_NODE: Record<string, NodeId> = {
  code_writer: 'write',
  code_reviewer: 'review',
  test_generator: 'tests',
  security_analyzer: 'security',
}

export interface Round {
  iteration: number
  summary: string | null
  files: string[]
  patch: string | null
  review?: { approved: boolean; comments: ReviewComment[] }
  security?: { findings: Finding[] }
  tests?: { files: FileEdit[] }
  testResult?: TestResult
  verdict?: { passed: boolean; tests_passed: boolean }
  agentErrors: Partial<Record<NodeId, string>>
}

export type Tone = 'neutral' | 'info' | 'good' | 'bad' | 'warn'

export interface TimelineItem {
  seq: number
  at: string
  title: string
  detail?: string
  tone: Tone
  node?: NodeId
}

export interface LlmCall {
  agent: string
  model: string
  costUsd: number | null
  promptTokens: number
  cachedTokens: number
  completionTokens: number
  latencyMs: number
  cacheHit: boolean
}

export type ViewStatus = 'waiting' | 'running' | 'passed' | 'failed' | 'aborted' | 'crashed'

export interface RunView {
  task: string | null
  status: ViewStatus
  error: string | null
  iteration: number
  maxIterations: number
  budgetUsd: number
  spentUsd: number
  tokens: { prompt: number; cached: number; completion: number }
  calls: LlmCall[]
  nodes: Record<NodeId, NodeStatus>
  activeNodes: NodeId[]
  contextFiles: string[]
  rounds: Round[]
  timeline: TimelineItem[]
  lastSeq: number
}

export function initialView(): RunView {
  return {
    task: null,
    status: 'waiting',
    error: null,
    iteration: 0,
    maxIterations: 3,
    budgetUsd: 0,
    spentUsd: 0,
    tokens: { prompt: 0, cached: 0, completion: 0 },
    calls: [],
    nodes: Object.fromEntries(NODES.map((n) => [n, 'idle'])) as Record<NodeId, NodeStatus>,
    activeNodes: [],
    contextFiles: [],
    rounds: [],
    timeline: [],
    lastSeq: -1,
  }
}

const usd = (n: number | null | undefined) => `$${(n ?? 0).toFixed(4)}`

function withLastRound(view: RunView, update: (r: Round) => Round): Round[] {
  if (!view.rounds.length) return view.rounds
  const rounds = view.rounds.slice()
  rounds[rounds.length - 1] = update(rounds[rounds.length - 1])
  return rounds
}

/** Folds one event into the view. Pure, so it works the same for live runs and replays. */
export function applyEvent(view: RunView, e: RunEvent): RunView {
  if (e.seq <= view.lastSeq) return view // duplicate after a reconnect
  const v: RunView = { ...view, lastSeq: e.seq }
  const item = (title: string, tone: Tone, extra: Partial<TimelineItem> = {}) =>
    (v.timeline = [...v.timeline, { seq: e.seq, at: e.at, title, tone, ...extra }])
  const d = e.data

  switch (e.type) {
    case 'run_started':
      v.task = d.task
      v.status = 'running'
      v.budgetUsd = d.budget_usd
      v.maxIterations = d.max_iterations
      item('Run started', 'info', { detail: d.task })
      break

    case 'run_resumed':
      v.status = 'running'
      v.error = null
      item('Run resumed from its last saved step', 'info')
      break

    case 'node_started': {
      const node = d.node as NodeId
      const nodes = { ...v.nodes }
      if (node === 'write') ROUND_NODES.forEach((n) => (nodes[n] = 'idle'))
      nodes[node] = 'running'
      v.nodes = nodes
      v.activeNodes = [...v.activeNodes.filter((n) => n !== node), node]
      break
    }

    case 'node_finished': {
      const node = d.node as NodeId
      const failed = Boolean(d.error)
      v.nodes = { ...v.nodes, [node]: failed ? 'failed' : 'done' }
      v.activeNodes = v.activeNodes.filter((n) => n !== node)
      const label = NODE_LABELS[node]

      if (node === 'gather_context') {
        v.contextFiles = d.files ?? []
        item(`${label} picked ${v.contextFiles.length} file(s)`, 'neutral', { node })
      } else if (node === 'write') {
        v.iteration = d.iteration ?? v.iteration + 1
        if (failed) {
          item(`${label} failed`, 'bad', { node, detail: d.error })
        } else {
          v.rounds = [
            ...v.rounds,
            {
              iteration: v.iteration,
              summary: d.summary,
              files: d.files ?? [],
              patch: d.patch,
              agentErrors: {},
            },
          ]
          item(`Round ${v.iteration}: ${label} proposed a change`, 'info', {
            node,
            detail: d.summary,
          })
        }
      } else if (node === 'review' || node === 'security' || node === 'tests') {
        if (failed) {
          v.rounds = withLastRound(v, (r) => ({
            ...r,
            agentErrors: { ...r.agentErrors, [node]: d.error },
          }))
          item(`${label} failed; the round continues without it`, 'warn', {
            node,
            detail: d.error,
          })
        } else {
          v.rounds = withLastRound(v, (r) => ({ ...r, [node]: d.output }))
          item(describeAgent(node, d.output), toneFor(node, d.output), { node })
        }
      } else if (node === 'run_tests') {
        const result = d.result as TestResult | null
        if (result) {
          v.rounds = withLastRound(v, (r) => ({ ...r, testResult: result }))
          item(
            result.passed
              ? 'Tests passed in the sandbox'
              : result.timed_out
                ? 'Tests timed out in the sandbox'
                : 'Tests failed in the sandbox',
            result.passed ? 'good' : 'bad',
            { node, detail: `${(result.duration_ms / 1000).toFixed(1)}s` },
          )
        }
      } else if (node === 'judge') {
        v.rounds = withLastRound(v, (r) => ({
          ...r,
          verdict: { passed: d.passed, tests_passed: d.tests_passed },
        }))
        if (d.passed) item('Judge: round passed', 'good', { node })
        else if (d.status === 'failed' || d.status === 'aborted')
          item(`Judge: stopping (${d.error})`, 'bad', { node })
        else item('Judge: sending feedback to CodeWriter', 'warn', { node })
      }
      break
    }

    case 'llm_call': {
      v.spentUsd += d.cost_usd ?? 0
      v.tokens = {
        prompt: v.tokens.prompt + d.prompt_tokens,
        cached: v.tokens.cached + d.cached_tokens,
        completion: v.tokens.completion + d.completion_tokens,
      }
      v.calls = [
        ...v.calls,
        {
          agent: d.agent,
          model: d.model,
          costUsd: d.cost_usd,
          promptTokens: d.prompt_tokens,
          cachedTokens: d.cached_tokens,
          completionTokens: d.completion_tokens,
          latencyMs: d.latency_ms,
          cacheHit: d.cache_hit,
        },
      ]
      const node = AGENT_NODE[d.agent]
      item(
        d.cache_hit ? `${d.model}: answered from cache` : `${d.model} call`,
        'neutral',
        {
          node,
          detail: d.cache_hit
            ? 'no cost'
            : `${d.prompt_tokens.toLocaleString()} in · ${d.completion_tokens.toLocaleString()} out · ${usd(d.cost_usd)}`,
        },
      )
      break
    }

    case 'run_finished':
      v.status = d.status
      v.error = d.error
      v.spentUsd = d.spent_usd
      v.activeNodes = []
      item(
        d.status === 'passed'
          ? `Passed after ${d.iterations} round(s)`
          : `Run ${d.status}${d.error ? `: ${d.error}` : ''}`,
        d.status === 'passed' ? 'good' : 'bad',
        { detail: `Total cost ${usd(d.spent_usd)}` },
      )
      break

    case 'run_crashed':
      v.status = 'crashed'
      v.error = d.error
      v.activeNodes = []
      item('Run crashed; it can be resumed', 'bad', { detail: d.error })
      break
  }
  return v
}

function describeAgent(node: NodeId, output: any): string {
  if (node === 'review') {
    const blocking = (output?.comments ?? []).filter((c: ReviewComment) =>
      ['blocker', 'major'].includes(c.severity),
    ).length
    return output?.approved
      ? 'CodeReviewer approved'
      : `CodeReviewer requested changes (${blocking} blocking)`
  }
  if (node === 'security') {
    const n = output?.findings?.length ?? 0
    return n ? `SecurityAnalyzer found ${n} issue(s)` : 'SecurityAnalyzer found no issues'
  }
  const n = output?.files?.length ?? 0
  return `TestGenerator wrote ${n} test file(s)`
}

function toneFor(node: NodeId, output: any): Tone {
  if (node === 'review') return output?.approved ? 'good' : 'warn'
  if (node === 'security') {
    const serious = (output?.findings ?? []).some((f: Finding) =>
      ['critical', 'high'].includes(f.severity),
    )
    return serious ? 'bad' : output?.findings?.length ? 'warn' : 'good'
  }
  return 'neutral'
}

export function replay(events: RunEvent[]): RunView {
  return events.reduce(applyEvent, initialView())
}
