export interface FileDiff {
  path: string
  isNew: boolean
  lines: { kind: 'add' | 'del' | 'ctx' | 'hunk'; text: string }[]
}

export function parsePatch(patch: string): FileDiff[] {
  const files: FileDiff[] = []
  let current: FileDiff | null = null
  let fromNull = false
  for (const line of patch.split('\n')) {
    if (line.startsWith('--- ')) {
      fromNull = line.includes('/dev/null')
    } else if (line.startsWith('+++ ')) {
      current = { path: line.slice(4).replace(/^b\//, ''), isNew: fromNull, lines: [] }
      files.push(current)
    } else if (current) {
      if (line.startsWith('@@')) current.lines.push({ kind: 'hunk', text: line })
      else if (line.startsWith('+')) current.lines.push({ kind: 'add', text: line.slice(1) })
      else if (line.startsWith('-')) current.lines.push({ kind: 'del', text: line.slice(1) })
      else if (line.length) current.lines.push({ kind: 'ctx', text: line.slice(1) })
    }
  }
  return files
}
