import { Fragment } from 'react'

/** Text with `inline code` spans, as written in task prompts and agent replies. */
export function Prose({ text }: { text: string | null | undefined }) {
  if (!text) return null
  return (
    <>
      {text.split(/(`[^`]+`)/g).map((part, i) =>
        part.startsWith('`') && part.endsWith('`') && part.length > 2 ? (
          <code
            key={i}
            className="rounded-md bg-ultramarine-500/10 px-1.5 py-0.5 font-mono text-[0.85em] text-accent"
          >
            {part.slice(1, -1)}
          </code>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  )
}
