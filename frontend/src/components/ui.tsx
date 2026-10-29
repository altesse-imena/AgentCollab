import type { ReactNode } from 'react'
import { type BadgeTone, cx } from '../lib/format'

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: 'bg-slate-800 text-slate-300 ring-slate-700',
  info: 'bg-brand-500/15 text-brand-300 ring-brand-500/30',
  good: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  warn: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  bad: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
}

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={cx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset',
        BADGE_TONES[tone],
      )}
    >
      {children}
    </span>
  )
}

export function Panel({
  title,
  action,
  children,
  className,
}: {
  title?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cx('rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur', className)}
    >
      {title && (
        <header className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}
