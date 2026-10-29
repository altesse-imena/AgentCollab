import { parsePatch } from '../lib/diff'
import { cx } from '../lib/format'

const LINE_STYLE = {
  add: 'bg-emerald-500/10 text-emerald-200',
  del: 'bg-rose-500/10 text-rose-200',
  ctx: 'text-slate-400',
  hunk: 'bg-brand-500/10 text-brand-300',
}

export function DiffView({ patch }: { patch: string | null }) {
  if (!patch) return <p className="p-4 text-sm text-slate-500">No changes.</p>
  return (
    <div className="space-y-3 p-4">
      {parsePatch(patch).map((file) => (
        <div key={file.path} className="overflow-hidden rounded-lg border border-slate-800">
          <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs text-slate-300">
            {file.path}
            {file.isNew && <span className="text-emerald-400">new file</span>}
          </div>
          <pre className="overflow-x-auto bg-slate-950 py-1 font-mono text-[12px] leading-5">
            {file.lines.map((l, i) => (
              <div key={i} className={cx('px-3', LINE_STYLE[l.kind])}>
                <span className="mr-3 inline-block w-3 select-none text-slate-600">
                  {l.kind === 'add' ? '+' : l.kind === 'del' ? '−' : ''}
                </span>
                {l.text || ' '}
              </div>
            ))}
          </pre>
        </div>
      ))}
    </div>
  )
}
