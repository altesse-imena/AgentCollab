import { CircleCheckBig, CircleX, FileText, type LucideIcon, RotateCcw } from 'lucide-react'
import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { AGENT_BY_ID } from '../../lib/agents'
import { cx, usd } from '../../lib/format'
import type { Round, RunView } from '../../lib/runState'
import { durationS, formatDuration, testCounts } from '../../lib/story'
import { Prose } from '../Prose'
import { Badge } from '../ui'
import { BeforeAfter } from './BeforeAfter'

const SEVERITY_TONE = {
  blocker: 'bad',
  major: 'bad',
  critical: 'bad',
  high: 'bad',
  minor: 'warn',
  medium: 'warn',
  nit: 'neutral',
  low: 'neutral',
} as const

function Chapter({
  n,
  icon: Icon,
  eyebrow,
  title,
  children,
}: {
  n: number
  icon: LucideIcon
  eyebrow: string
  title: ReactNode
  children: ReactNode
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="relative grid gap-6 md:grid-cols-[120px_1fr]"
    >
      <div className="flex items-center gap-3 md:sticky md:top-24 md:flex-col md:items-start md:self-start">
        <span className="font-heading text-5xl leading-none text-ultramarine-500/40 md:text-6xl">
          {String(n).padStart(2, '0')}
        </span>
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-card text-accent">
          <Icon className="h-5 w-5" strokeWidth={1.75} />
        </span>
      </div>
      <div className="min-w-0 rounded-3xl border border-line bg-card p-6 shadow-lg shadow-slate-200/40 backdrop-blur-sm md:p-8 dark:shadow-black/20">
        <p className="text-[11px] font-semibold tracking-[0.2em] text-faint uppercase">{eyebrow}</p>
        <h3 className="mt-2 text-2xl text-ink md:text-3xl">{title}</h3>
        <div className="mt-6">{children}</div>
      </div>
    </motion.section>
  )
}

function Quote({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'warn' | 'bad'
}) {
  return (
    <blockquote
      className={cx(
        'border-l-2 py-1 pl-4 text-base leading-relaxed text-body',
        tone === 'bad'
          ? 'border-rose-400'
          : tone === 'warn'
            ? 'border-amber-400'
            : 'border-ultramarine-400',
      )}
    >
      {children}
    </blockquote>
  )
}

function AgentFailed({ message }: { message?: string }) {
  return message ? (
    <p className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-warn">
      This agent failed this round, so the judge decided without it: {message}
    </p>
  ) : null
}

function roundChapters(round: Round, isLast: boolean, passed: boolean, start: number) {
  const chapters: ReactNode[] = []
  let n = start
  const writer = AGENT_BY_ID.write!
  chapters.push(
    <Chapter
      key={`w${round.iteration}`}
      n={n++}
      icon={writer.icon}
      eyebrow={`Round ${round.iteration} · Writer`}
      title={round.iteration === 1 ? 'The first draft' : 'The rework'}
    >
      {round.summary && (
        <p className="mb-6 text-lg leading-relaxed text-body">
          <Prose text={round.summary} />
        </p>
      )}
      <BeforeAfter patch={round.patch} />
    </Chapter>,
  )

  const review = round.review
  chapters.push(
    <Chapter
      key={`r${round.iteration}`}
      n={n++}
      icon={AGENT_BY_ID.review!.icon}
      eyebrow={`Round ${round.iteration} · Reviewer`}
      title={!review ? 'No review this round' : review.approved ? 'Approved' : 'Changes requested'}
    >
      <AgentFailed message={round.agentErrors.review} />
      {review && review.comments.length === 0 && (
        <p className="text-body">The reviewer read the diff and had nothing to add.</p>
      )}
      <div className="space-y-5">
        {review?.comments.map((c, i) => (
          <div key={i}>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone={SEVERITY_TONE[c.severity]}>{c.severity}</Badge>
              <span className="font-mono text-xs text-faint">
                {c.path}
                {c.line ? `:${c.line}` : ''}
              </span>
            </div>
            <Quote tone={SEVERITY_TONE[c.severity] === 'bad' ? 'bad' : 'neutral'}>
              <Prose text={c.message} />
            </Quote>
          </div>
        ))}
      </div>
    </Chapter>,
  )

  const findings = round.security?.findings ?? []
  chapters.push(
    <Chapter
      key={`s${round.iteration}`}
      n={n++}
      icon={AGENT_BY_ID.security!.icon}
      eyebrow={`Round ${round.iteration} · Security`}
      title={
        !round.security
          ? 'No security pass this round'
          : findings.length
            ? `${findings.length} ${findings.length === 1 ? 'issue' : 'issues'} flagged`
            : 'Nothing exploitable found'
      }
    >
      <AgentFailed message={round.agentErrors.security} />
      {round.security && findings.length === 0 && (
        <p className="text-body">
          The security agent checked the change for injection, unsafe file access, secrets and other
          common flaws, and found none.
        </p>
      )}
      <div className="space-y-5">
        {findings.map((f, i) => (
          <div key={i}>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone={SEVERITY_TONE[f.severity]}>{f.severity}</Badge>
              {f.cwe && <Badge>{f.cwe}</Badge>}
              <span className="font-mono text-xs text-faint">
                {f.path}
                {f.line ? `:${f.line}` : ''}
              </span>
            </div>
            <Quote tone={SEVERITY_TONE[f.severity] === 'bad' ? 'bad' : 'warn'}>
              <Prose text={f.issue} />
            </Quote>
            <p className="mt-2 pl-4 text-sm text-muted">
              <span className="font-medium text-body">Suggested fix:</span> <Prose text={f.fix} />
            </p>
          </div>
        ))}
      </div>
    </Chapter>,
  )

  const result = round.testResult
  const counts = testCounts(result?.output)
  chapters.push(
    <Chapter
      key={`t${round.iteration}`}
      n={n++}
      icon={AGENT_BY_ID.tests!.icon}
      eyebrow={`Round ${round.iteration} · Tester and sandbox`}
      title={
        !result
          ? 'Tests were not run'
          : result.passed
            ? `${counts.passed || 'All'} tests, all green`
            : result.timed_out
              ? 'The tests timed out'
              : `${counts.failed || 'Some'} ${counts.failed === 1 ? 'test' : 'tests'} failing`
      }
    >
      <AgentFailed message={round.agentErrors.tests} />
      <p className="mb-4 text-body">
        The tester wrote {round.tests?.files.length ?? 0} test{' '}
        {round.tests?.files.length === 1 ? 'file' : 'files'}, then everything ran in a sandbox with
        no network and a read-only filesystem
        {result ? `, in ${(result.duration_ms / 1000).toFixed(1)}s` : ''}.
      </p>
      {result && (
        <pre className="max-h-56 overflow-auto rounded-xl border border-line bg-sunken p-4 font-mono text-[12px] leading-5 text-muted">
          {result.output.trim()}
        </pre>
      )}
      {round.tests?.files.map((f) => (
        <details key={f.path} className="group mt-3">
          <summary className="cursor-pointer text-sm text-accent hover:underline">
            Show {f.path}
          </summary>
          <pre className="mt-2 max-h-96 overflow-auto rounded-xl border border-line bg-sunken p-4 font-mono text-[12px] leading-5 text-body">
            {f.content}
          </pre>
        </details>
      ))}
    </Chapter>,
  )

  if (!isLast || !passed) {
    const reasons = [
      result && !result.passed && 'tests failed',
      review && !review.approved && 'the reviewer asked for changes',
      findings.some((f) => ['critical', 'high'].includes(f.severity)) &&
        'serious security findings',
    ].filter(Boolean)
    chapters.push(
      <Chapter
        key={`j${round.iteration}`}
        n={n++}
        icon={isLast ? CircleX : RotateCcw}
        eyebrow={`Round ${round.iteration} · Judge`}
        title={isLast ? 'Out of rounds' : 'Sent back for another round'}
      >
        <p className="text-lg leading-relaxed text-body">
          {reasons.length ? `The round failed because ${reasons.join(', ')}. ` : ''}
          {isLast
            ? 'The run stopped here without a change that passed every check.'
            : 'Every failure went back to the Writer as feedback for the next draft.'}
        </p>
      </Chapter>,
    )
  }
  return { chapters, next: n }
}

/** A finished run told as a case study you scroll through. */
export function Story({ view }: { view: RunView }) {
  if (!view.rounds.length)
    return <p className="py-24 text-center text-muted">This run has no recorded rounds yet.</p>

  const passed = view.status === 'passed'
  let n = 1
  const brief = (
    <Chapter
      key="brief"
      n={n++}
      icon={FileText}
      eyebrow="The brief"
      title="What the agents were asked to do"
    >
      <Quote>
        <span className="text-lg">
          <Prose text={view.task} />
        </span>
      </Quote>
      {view.contextFiles.length > 0 && (
        <p className="mt-6 text-sm text-muted">
          The context step picked the files to work from:{' '}
          {view.contextFiles.map((f) => (
            <code
              key={f}
              className="mr-1.5 rounded-md bg-sunken px-1.5 py-0.5 font-mono text-xs text-body"
            >
              {f}
            </code>
          ))}
        </p>
      )}
    </Chapter>
  )

  const rounds: ReactNode[] = []
  view.rounds.forEach((round, i) => {
    const { chapters, next } = roundChapters(round, i === view.rounds.length - 1, passed, n)
    n = next
    rounds.push(...chapters)
  })

  const seconds = durationS(view)
  const tokens = view.tokens.prompt + view.tokens.completion
  return (
    <div className="space-y-10 md:space-y-14">
      {brief}
      {rounds}
      <motion.section
        initial={{ opacity: 0, scale: 0.97 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className={cx(
          'relative overflow-hidden rounded-3xl border p-8 text-center md:p-14',
          passed ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-rose-500/30 bg-rose-500/5',
        )}
      >
        {passed ? (
          <CircleCheckBig className="mx-auto h-14 w-14 text-emerald-400" strokeWidth={1.5} />
        ) : (
          <CircleX className="mx-auto h-14 w-14 text-rose-400" strokeWidth={1.5} />
        )}
        <h3 className="mt-4 text-3xl text-ink md:text-4xl">
          {passed
            ? `Shipped after ${view.iteration} ${view.iteration === 1 ? 'round' : 'rounds'}`
            : 'No passing change'}
        </h3>
        <p className="mx-auto mt-3 max-w-xl text-muted">
          {passed
            ? 'The tests passed, the reviewer approved, and no serious security findings were left open.'
            : (view.error ?? 'The agents ran out of rounds before every check passed.')}
        </p>
        <dl className="mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-6 md:grid-cols-4">
          {[
            ['Rounds', String(view.iteration)],
            ['Time', seconds ? formatDuration(seconds) : '–'],
            ['Model calls', String(view.calls.length)],
            ['Cost', usd(view.spentUsd)],
          ].map(([label, value]) => (
            <div key={label}>
              <dd className="font-heading text-3xl text-ink md:text-4xl">{value}</dd>
              <dt className="mt-1 text-xs tracking-[0.18em] text-faint uppercase">{label}</dt>
            </div>
          ))}
        </dl>
        <p className="mt-6 text-xs text-faint">{tokens.toLocaleString()} tokens in total</p>
      </motion.section>
    </div>
  )
}
