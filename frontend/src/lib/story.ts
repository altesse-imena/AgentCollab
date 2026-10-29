// Plain-language descriptions of runs, for the stage narration, agent cards and story mode.
import type { NodeId, Round, RunView, Tone } from './runState'
import type { RunSummary, Task } from './types'

const ACRONYMS: Record<string, string> = { sql: 'SQL', lru: 'LRU', csv: 'CSV', api: 'API' }

/** "sql_injection" -> "SQL injection", "paginate_off_by_one" -> "Paginate off-by-one" */
export function humanize(id: string): string {
  const words = id
    .replace(/off_by_one/g, 'off-by-one')
    .split('_')
    .map((w) => ACRONYMS[w] ?? w)
  const first = words[0]
  words[0] = first === first.toUpperCase() ? first : first[0].toUpperCase() + first.slice(1)
  return words.join(' ')
}

export const KIND_LABEL = { feature: 'Feature', bug: 'Bug fix', security: 'Security fix' } as const

export function taskFor(prompt: string | null | undefined, tasks: Task[]): Task | undefined {
  return prompt ? tasks.find((t) => t.prompt === prompt) : undefined
}

export function titleFor(prompt: string | null | undefined, tasks: Task[]): string {
  const task = taskFor(prompt, tasks)
  if (task) return humanize(task.id)
  const words = (prompt ?? '').replace(/`/g, '').split(/\s+/).slice(0, 6).join(' ')
  return words || 'Untitled run'
}

export function firstSentence(text: string | null | undefined): string {
  if (!text) return ''
  // split on ". " but not inside `code` spans
  let inCode = false
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '`') inCode = !inCode
    if (!inCode && text[i] === '.' && (text[i + 1] === ' ' || i === text.length - 1))
      return text.slice(0, i + 1)
  }
  return text
}

export function testCounts(output: string | undefined): { passed: number; failed: number } {
  const num = (re: RegExp) => Number(output?.match(re)?.[1] ?? 0)
  return { passed: num(/(\d+) passed/), failed: num(/(\d+) failed/) + num(/(\d+) error/) }
}

export function durationS(view: RunView): number {
  const t = view.timeline
  if (t.length < 2) return 0
  return (new Date(t[t.length - 1].at).getTime() - new Date(t[0].at).getTime()) / 1000
}

export const formatDuration = (s: number) =>
  s < 60 ? `${Math.round(s)}s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export interface Narration {
  key: string // changes whenever the headline should animate in again
  headline: string
  detail?: string
  tone: Tone
}

/** One sentence about what is happening right now, for the stage caption. */
export function narrate(view: RunView): Narration {
  const round = view.rounds[view.rounds.length - 1]
  const r = view.iteration
  if (view.status === 'waiting')
    return { key: 'wait', headline: 'Connecting to the run…', tone: 'neutral' }
  if (view.status === 'passed') {
    const tests = testCounts(round?.testResult?.output).passed
    return {
      key: 'passed',
      headline: `Shipped. Every check passed after ${plural(r, 'round')}.`,
      detail: [tests && `${plural(tests, 'test')} green`, durationLabel(view)]
        .filter(Boolean)
        .join(' · '),
      tone: 'good',
    }
  }
  if (['failed', 'aborted', 'crashed'].includes(view.status)) {
    return {
      key: 'stopped',
      headline:
        view.status === 'crashed'
          ? 'The run crashed partway through.'
          : `Stopped after ${plural(r, 'round')} without a passing change.`,
      detail: view.error ?? undefined,
      tone: 'bad',
    }
  }

  const active = new Set(view.activeNodes)
  const inspecting = (['review', 'tests', 'security'] as NodeId[]).filter((n) => active.has(n))
  if (active.has('gather_context'))
    return {
      key: 'ctx',
      headline: 'Reading the repository to find the files that matter.',
      tone: 'info',
    }
  if (active.has('write'))
    return r >= 1
      ? {
          key: `write-${r}`,
          headline: `The judge sent it back. Writer is reworking the change (round ${r + 1}).`,
          detail: 'Every failed test, review comment and security finding goes back to the Writer.',
          tone: 'warn',
        }
      : {
          key: 'write-0',
          headline: 'Writer is drafting the change.',
          detail: view.contextFiles.length
            ? `Working from ${plural(view.contextFiles.length, 'file')}: ${view.contextFiles.join(', ')}`
            : undefined,
          tone: 'info',
        }
  if (inspecting.length)
    return {
      key: `inspect-${r}-${inspecting.join()}`,
      headline: `${listNames(inspecting)} ${inspecting.length > 1 ? 'are' : 'is'} inspecting the change in parallel.`,
      detail: round?.summary ?? undefined,
      tone: 'info',
    }
  if (active.has('run_tests'))
    return {
      key: `sandbox-${r}`,
      headline: 'Running the tests in a locked-down sandbox.',
      detail: 'No network, read-only filesystem, capped CPU and memory.',
      tone: 'info',
    }
  if (active.has('judge'))
    return { key: `judge-${r}`, headline: 'The judge is weighing every result.', tone: 'info' }

  const last = [...view.timeline]
    .reverse()
    .find((t) => t.tone !== 'neutral' || t.node === 'gather_context')
  return {
    key: `last-${last?.seq ?? 0}`,
    headline: last?.title ?? 'Starting…',
    detail: last?.detail,
    tone: last?.tone ?? 'info',
  }
}

const NAMES: Partial<Record<NodeId, string>> = {
  review: 'Reviewer',
  tests: 'Tester',
  security: 'Security',
}
function listNames(ids: NodeId[]) {
  const names = ids.map((id) => NAMES[id] ?? id)
  return names.length > 1
    ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
    : names[0]
}

function durationLabel(view: RunView) {
  const s = durationS(view)
  return s ? `${formatDuration(s)} start to finish` : ''
}

export interface Speech {
  status: string
  quote?: string
  tone: Tone
}

/** What each agent "said" in a round, in plain language, for the agent cards. */
export function speechFor(id: NodeId, round: Round | undefined, running: boolean): Speech {
  if (running) return { status: 'Working…', tone: 'info' }
  if (!round) return { status: 'Waiting for the first draft', tone: 'neutral' }
  const error = round.agentErrors[id]
  if (error) return { status: 'Failed this round', quote: error, tone: 'warn' }
  switch (id) {
    case 'write':
      return {
        status: `Changed ${plural(round.files.length, 'file')}`,
        quote: round.summary ?? undefined,
        tone: 'info',
      }
    case 'review': {
      if (!round.review) return { status: 'Waiting for the draft', tone: 'neutral' }
      const top = round.review.comments[0]
      return {
        status: round.review.approved
          ? round.review.comments.length
            ? `Approved, with ${plural(round.review.comments.length, 'note')}`
            : 'Approved'
          : 'Requested changes',
        quote: top?.message,
        tone: round.review.approved ? 'good' : 'warn',
      }
    }
    case 'security': {
      if (!round.security) return { status: 'Waiting for the draft', tone: 'neutral' }
      const f = round.security.findings
      const serious = f.some((x) => ['critical', 'high'].includes(x.severity))
      return f.length
        ? {
            status: `Flagged ${plural(f.length, 'issue')}`,
            quote: `${f[0].cwe ? `${f[0].cwe}: ` : ''}${f[0].issue}`,
            tone: serious ? 'bad' : 'warn',
          }
        : { status: 'No vulnerabilities found', tone: 'good' }
    }
    case 'tests': {
      if (!round.tests && !round.testResult)
        return { status: 'Waiting for the draft', tone: 'neutral' }
      const files = round.tests?.files.length ?? 0
      const result = round.testResult
      if (!result) return { status: `Wrote ${plural(files, 'test file')}`, tone: 'neutral' }
      const { passed, failed } = testCounts(result.output)
      return result.passed
        ? {
            status: `${plural(passed, 'test')} passing`,
            quote: `Wrote ${plural(files, 'test file')}; all green in the sandbox.`,
            tone: 'good',
          }
        : {
            status: result.timed_out ? 'Tests timed out' : `${failed || 'Some'} failing`,
            quote: lastLines(result.output, 2),
            tone: 'bad',
          }
    }
    default:
      return { status: '', tone: 'neutral' }
  }
}

function lastLines(text: string, n: number) {
  return text.trim().split('\n').slice(-n).join(' ').trim()
}

export interface Showcase {
  finished: number
  passRate: number
  avgCost: number
  avgSeconds: number | null
}

export function showcaseStats(runs: RunSummary[]): Showcase {
  const done = runs.filter((r) => r.status === 'passed' || r.status === 'failed')
  const timed = done.filter((r) => r.finished_at)
  const secs = timed.map(
    (r) => (new Date(r.finished_at!).getTime() - new Date(r.created_at).getTime()) / 1000,
  )
  return {
    finished: done.length,
    passRate: done.length ? done.filter((r) => r.status === 'passed').length / done.length : 0,
    avgCost: done.length ? done.reduce((s, r) => s + r.spent_usd, 0) / done.length : 0,
    avgSeconds: secs.length ? secs.reduce((a, b) => a + b, 0) / secs.length : null,
  }
}
