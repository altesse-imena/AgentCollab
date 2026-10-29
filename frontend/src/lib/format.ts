export function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export type BadgeTone = 'neutral' | 'info' | 'good' | 'warn' | 'bad'

export const STATUS_TONE: Record<string, BadgeTone> = {
  waiting: 'neutral',
  running: 'info',
  passed: 'good',
  failed: 'bad',
  aborted: 'warn',
  crashed: 'bad',
}

export const KIND_TONE: Record<string, BadgeTone> = {
  feature: 'info',
  bug: 'warn',
  security: 'bad',
}

export const usd = (n: number | null | undefined, digits = 4) => `$${(n ?? 0).toFixed(digits)}`

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
