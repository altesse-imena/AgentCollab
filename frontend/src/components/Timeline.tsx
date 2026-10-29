import { useEffect, useRef } from 'react'
import { cx } from '../lib/format'
import type { TimelineItem, Tone } from '../lib/runState'

const DOT: Record<Tone, string> = {
  neutral: 'bg-slate-600',
  info: 'bg-brand-400',
  good: 'bg-emerald-400',
  warn: 'bg-amber-400',
  bad: 'bg-rose-400',
}

export function Timeline({ items }: { items: TimelineItem[] }) {
  const box = useRef<HTMLDivElement>(null)
  // keep the newest event in view by scrolling this panel only, never the page
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: 'smooth' })
  }, [items.length])

  if (!items.length) return <p className="p-4 text-sm text-slate-500">Waiting for events…</p>
  const start = new Date(items[0].at).getTime()
  return (
    <div ref={box} className="h-full overflow-y-auto">
      <ol className="space-y-0.5 p-3">
        {items.map((item) => (
          <li key={item.seq} className="flex gap-3 rounded-md px-2 py-1.5 hover:bg-slate-800/40">
            <span className="w-12 shrink-0 pt-0.5 text-right font-mono text-[11px] text-slate-500">
              +{((new Date(item.at).getTime() - start) / 1000).toFixed(1)}s
            </span>
            <span className={cx('mt-1.5 h-2 w-2 shrink-0 rounded-full', DOT[item.tone])} />
            <div className="min-w-0">
              <p className="text-[13px] text-slate-200">{item.title}</p>
              {item.detail && <p className="line-clamp-3 text-xs text-slate-500">{item.detail}</p>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
