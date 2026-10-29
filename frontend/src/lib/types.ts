export type EventType =
  | 'run_started'
  | 'node_started'
  | 'node_finished'
  | 'llm_call'
  | 'run_finished'
  | 'run_crashed'
  | 'run_resumed'

export interface RunEvent {
  seq: number
  type: EventType
  data: Record<string, any>
  at: string
}

export interface Task {
  id: string
  kind: 'feature' | 'bug' | 'security'
  prompt: string
}

export type RunStatus = 'running' | 'passed' | 'failed' | 'aborted'

export interface RunSummary {
  id: string
  task: string
  status: RunStatus
  spent_usd: number
  budget_usd: number
  created_at: string
  finished_at: string | null
  error: string | null
}

export interface ReviewComment {
  path: string
  line: number | null
  severity: 'blocker' | 'major' | 'minor' | 'nit'
  message: string
}

export interface Finding {
  path: string
  line: number | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  cwe: string | null
  issue: string
  fix: string
}

export interface FileEdit {
  path: string
  content: string
}

export interface TestResult {
  passed: boolean
  exit_code: number | null
  output: string
  duration_ms: number
  timed_out: boolean
}
