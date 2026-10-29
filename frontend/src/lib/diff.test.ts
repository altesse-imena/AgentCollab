import { describe, expect, it } from 'vitest'
import { parsePatch } from './diff'

describe('parsePatch', () => {
  it('splits files and classifies lines', () => {
    const patch = [
      '--- a/app.py',
      '+++ b/app.py',
      '@@ -1 +1,2 @@',
      '-x = 1',
      '+x = 2',
      '+y = 3',
      '--- /dev/null',
      '+++ b/tests/test_app.py',
      '@@ -0,0 +1 @@',
      '+def test(): ...',
    ].join('\n')
    const files = parsePatch(patch)
    expect(files.map((f) => [f.path, f.isNew])).toEqual([
      ['app.py', false],
      ['tests/test_app.py', true],
    ])
    expect(files[0].lines.map((l) => l.kind)).toEqual(['hunk', 'del', 'add', 'add'])
  })
})
