import { describe, expect, it } from 'vitest'
import { initialView, type Round } from './runState'
import { firstSentence, humanize, narrate, speechFor, testCounts } from './story'

describe('humanize', () => {
  it('turns task ids into titles', () => {
    expect(humanize('sql_injection')).toBe('SQL injection')
    expect(humanize('paginate_off_by_one')).toBe('Paginate off-by-one')
    expect(humanize('lru_cache')).toBe('LRU cache')
  })
})

describe('firstSentence', () => {
  it('ignores full stops inside code spans', () => {
    expect(firstSentence('`read_upload` in uploads.py is unsafe. Fix it.')).toBe(
      '`read_upload` in uploads.py is unsafe.',
    )
  })
})

describe('testCounts', () => {
  it('reads pytest summaries', () => {
    expect(testCounts('3 failed, 5 passed in 0.1s')).toEqual({ passed: 5, failed: 3 })
  })
})

describe('narrate', () => {
  it('describes the parallel inspectors', () => {
    const view = {
      ...initialView(),
      status: 'running' as const,
      activeNodes: ['review' as const, 'security' as const],
    }
    expect(narrate(view).headline).toBe(
      'Reviewer and Security are inspecting the change in parallel.',
    )
  })

  it('calls out a rework round', () => {
    const view = {
      ...initialView(),
      status: 'running' as const,
      iteration: 1,
      activeNodes: ['write' as const],
    }
    expect(narrate(view).headline).toContain('round 2')
  })
})

describe('speechFor', () => {
  const round: Round = {
    iteration: 1,
    summary: 'Use parameters',
    files: ['users.py'],
    patch: null,
    agentErrors: {},
    security: {
      findings: [
        {
          path: 'users.py',
          line: 3,
          severity: 'high',
          cwe: 'CWE-89',
          issue: 'SQL injection',
          fix: 'bind',
        },
      ],
    },
  }
  it('summarises security findings', () => {
    expect(speechFor('security', round, false)).toMatchObject({
      status: 'Flagged 1 issue',
      quote: 'CWE-89: SQL injection',
      tone: 'bad',
    })
  })
})
