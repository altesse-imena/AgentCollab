import {
  Eye,
  FlaskConical,
  FolderSearch,
  type LucideIcon,
  PenLine,
  Scale,
  ShieldCheck,
  SquareTerminal,
} from 'lucide-react'
import type { NodeId } from './runState'

export interface Agent {
  id: NodeId
  name: string
  role: string
  icon: LucideIcon
  ai: boolean // a model call, as opposed to a plain step
}

// The steps drawn on the stage. `finalize` only packages the result, so it isn't shown.
export const AGENTS: Agent[] = [
  { id: 'gather_context', name: 'Context', role: 'reads the repo', icon: FolderSearch, ai: false },
  { id: 'write', name: 'Writer', role: 'writes the change', icon: PenLine, ai: true },
  { id: 'review', name: 'Reviewer', role: 'reviews the diff', icon: Eye, ai: true },
  { id: 'tests', name: 'Tester', role: 'writes tests', icon: FlaskConical, ai: true },
  {
    id: 'security',
    name: 'Security',
    role: 'hunts for vulnerabilities',
    icon: ShieldCheck,
    ai: true,
  },
  { id: 'run_tests', name: 'Sandbox', role: 'runs the tests', icon: SquareTerminal, ai: false },
  { id: 'judge', name: 'Judge', role: 'ships it or sends it back', icon: Scale, ai: false },
]

export const AGENT_BY_ID = Object.fromEntries(AGENTS.map((a) => [a.id, a])) as Record<
  NodeId,
  Agent | undefined
>

export const LINKS: [NodeId, NodeId][] = [
  ['gather_context', 'write'],
  ['write', 'review'],
  ['write', 'tests'],
  ['write', 'security'],
  ['review', 'run_tests'],
  ['tests', 'run_tests'],
  ['security', 'run_tests'],
  ['run_tests', 'judge'],
]
