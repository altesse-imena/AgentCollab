import { useState } from 'react'
import { parsePatch } from '../../lib/diff'
import { cx } from '../../lib/format'

type Line = { text: string; changed: boolean } | 'gap'

function sides(lines: ReturnType<typeof parsePatch>[number]['lines']) {
  const before: Line[] = []
  const after: Line[] = []
  for (const l of lines) {
    if (l.kind === 'hunk') {
      if (before.length) before.push('gap')
      if (after.length) after.push('gap')
    } else if (l.kind === 'ctx') {
      before.push({ text: l.text, changed: false })
      after.push({ text: l.text, changed: false })
    } else if (l.kind === 'del') before.push({ text: l.text, changed: true })
    else after.push({ text: l.text, changed: true })
  }
  return { before, after }
}

function Code({ title, lines, tone }: { title: string; lines: Line[]; tone: 'before' | 'after' }) {
  return (
    <div className="min-w-0 overflow-hidden rounded-xl border border-line bg-sunken">
      <div className="flex items-center gap-2 border-b border-line px-4 py-2 text-[11px] font-semibold tracking-[0.18em] text-faint uppercase">
        <span
          className={cx(
            'h-2 w-2 rounded-full',
            tone === 'before' ? 'bg-rose-400' : 'bg-emerald-400',
          )}
        />
        {title}
      </div>
      <pre className="overflow-x-auto py-2 font-mono text-[12.5px] leading-6">
        {lines.length === 0 && <div className="px-4 text-faint italic">(new file)</div>}
        {lines.map((l, i) =>
          l === 'gap' ? (
            <div key={i} className="px-4 text-faint select-none">
              ⋯
            </div>
          ) : (
            <div
              key={i}
              className={cx(
                'px-4',
                l.changed
                  ? tone === 'before'
                    ? 'bg-rose-500/10 text-bad'
                    : 'bg-emerald-500/10 text-good'
                  : 'text-muted',
              )}
            >
              {l.text || ' '}
            </div>
          ),
        )}
      </pre>
    </div>
  )
}

/** The change as two panes: the code before and after, for each file touched. */
export function BeforeAfter({ patch }: { patch: string | null }) {
  const [expanded, setExpanded] = useState(false)
  if (!patch) return <p className="text-sm text-faint">No code changed.</p>
  const files = parsePatch(patch)
  const long = files.reduce((n, f) => n + f.lines.length, 0) > 28
  return (
    <div className="space-y-6">
      {files.map((file) => {
        const { before, after } = sides(file.lines)
        return (
          <div key={file.path}>
            <p className="mb-2 font-mono text-xs text-muted">
              {file.path}
              {file.isNew && <span className="ml-2 text-good">new file</span>}
            </p>
            <div
              className={cx(
                'relative grid gap-3 lg:grid-cols-2',
                long && !expanded && 'max-h-[420px] overflow-hidden',
              )}
            >
              <Code title="Before" lines={before} tone="before" />
              <Code title="After" lines={after} tone="after" />
              {long && !expanded && (
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-linear-to-t from-canvas to-transparent" />
              )}
            </div>
          </div>
        )
      })}
      {long && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="pill-outline px-4 py-1.5 text-xs"
        >
          {expanded ? 'Show less' : 'Show the whole change'}
        </button>
      )}
    </div>
  )
}
