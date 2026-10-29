import type { ReactNode } from 'react'
import { type BadgeTone, cx } from '../lib/format'

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: 'bg-hover text-body ring-line-strong',
  info: 'bg-brand-500/15 text-accent ring-brand-500/30',
  good: 'bg-emerald-500/15 text-good ring-emerald-500/30',
  warn: 'bg-amber-500/15 text-warn ring-amber-500/30',
  bad: 'bg-rose-500/15 text-bad ring-rose-500/30',
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
      className={cx(
        'rounded-xl border border-line bg-card shadow-lg shadow-slate-200/50 backdrop-blur-sm transition-colors duration-300 hover:border-brand-500/30 dark:shadow-black/20',
        className,
      )}
    >
      {title && (
        <header className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="text-xs font-medium tracking-widest text-muted uppercase">{title}</h2>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}
