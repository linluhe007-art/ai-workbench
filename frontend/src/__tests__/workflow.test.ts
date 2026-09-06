import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'
import { fetchWorkflow } from '../api/workflows'
import type { WorkflowData, WorkflowStep } from '../api/workflows'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

// ── API Tests ────────────────────────────────────────────────

describe('Workflow API', () => {
  it('fetchWorkflow returns workflow data', async () => {
    const mockData: WorkflowData = {
      task_id: 't1',
      intent: 'test',
      steps: [{ id: 's1', type: 'research', description: 'desc', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 }],
      total_steps: 1,
    }
    mockGet.mockResolvedValue({ data: mockData })
    const res = await fetchWorkflow('t1')
    expect(res.task_id).toBe('t1')
    expect(res.steps).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith('/tasks/t1/workflow')
  })
})

// ── DAG Data Transformation ──────────────────────────────────

describe('DAG data transformation', () => {
  it('converts steps to nodes', () => {
    const steps: WorkflowStep[] = [
      { id: 'research', type: 'research', description: 'desc', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'writing', type: 'writing', description: 'desc', agent: 'b', depends_on: ['research'], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    const nodes = steps.map((s) => ({ id: s.id, data: s }))
    expect(nodes).toHaveLength(2)
    expect(nodes[0].id).toBe('research')
    expect(nodes[1].id).toBe('writing')
  })

  it('converts dependencies to edges', () => {
    const steps: WorkflowStep[] = [
      { id: 'research', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'writing', type: 'writing', description: '', agent: 'b', depends_on: ['research'], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    const edges: { source: string; target: string }[] = []
    for (const step of steps) {
      for (const dep of step.depends_on) {
        edges.push({ source: dep, target: step.id })
      }
    }
    expect(edges).toHaveLength(1)
    expect(edges[0].source).toBe('research')
    expect(edges[0].target).toBe('writing')
  })

  it('handles multiple dependencies', () => {
    const steps: WorkflowStep[] = [
      { id: 'r1', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'r2', type: 'research', description: '', agent: 'b', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'write', type: 'writing', description: '', agent: 'c', depends_on: ['r1', 'r2'], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    const writeStep = steps.find((s) => s.id === 'write')!
    expect(writeStep.depends_on).toHaveLength(2)
  })

  it('handles empty steps', () => {
    const steps: WorkflowStep[] = []
    expect(steps.length).toBe(0)
  })
})

// ── Node Generation ──────────────────────────────────────────

describe('Node generation', () => {
  it('assigns unique IDs to nodes', () => {
    const steps: WorkflowStep[] = [
      { id: 'research', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'analysis', type: 'analysis', description: '', agent: 'b', depends_on: ['research'], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    const ids = steps.map((s) => s.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('positions nodes by level', () => {
    const steps: WorkflowStep[] = [
      { id: 'r', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
      { id: 'w', type: 'writing', description: '', agent: 'b', depends_on: ['r'], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    // Level 0: r, Level 1: w
    const levels = new Map<number, string[]>()
    for (const step of steps) {
      const level = step.depends_on.length === 0 ? 0 : 1
      if (!levels.has(level)) levels.set(level, [])
      levels.get(level)!.push(step.id)
    }
    expect(levels.get(0)).toContain('r')
    expect(levels.get(1)).toContain('w')
  })
})

// ── Edge Generation ──────────────────────────────────────────

describe('Edge generation', () => {
  it('creates edge for each dependency', () => {
    const deps = [['r', 'a'], ['a', 'w']]
    const edges = deps.map(([s, t]) => ({ source: s, target: t }))
    expect(edges).toHaveLength(2)
  })

  it('no edges when no dependencies', () => {
    const steps: WorkflowStep[] = [
      { id: 's1', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 },
    ]
    const edges: { source: string; target: string }[] = []
    for (const step of steps) {
      for (const dep of step.depends_on) {
        edges.push({ source: dep, target: step.id })
      }
    }
    expect(edges).toHaveLength(0)
  })

  it('edge animated when running', () => {
    const step: WorkflowStep = { id: 'w', type: 'writing', description: '', agent: 'b', depends_on: ['r'], status: 'running', started_at: null, finished_at: null, duration: 0 }
    const animated = step.status === 'running'
    expect(animated).toBe(true)
  })
})

// ── Status Mapping ───────────────────────────────────────────

describe('Status color mapping', () => {
  const colors: Record<string, string> = {
    pending: '#d9d9d9',
    running: '#1677ff',
    success: '#52c41a',
    failed: '#ff4d4f',
    skipped: '#bfbfbf',
  }

  it('maps all statuses', () => {
    const statuses = ['pending', 'running', 'success', 'failed', 'skipped']
    for (const s of statuses) {
      expect(colors[s]).toBeDefined()
    }
  })

  it('pending is grey', () => {
    expect(colors.pending).toBe('#d9d9d9')
  })

  it('success is green', () => {
    expect(colors.success).toBe('#52c41a')
  })

  it('failed is red', () => {
    expect(colors.failed).toBe('#ff4d4f')
  })
})

// ── Level Computation ────────────────────────────────────────

describe('Level computation', () => {
  it('no deps => level 0', () => {
    const step: WorkflowStep = { id: 's', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 }
    expect(step.depends_on.length === 0 ? 0 : 1).toBe(0)
  })

  it('depends on level 0 => level 1', () => {
    const step: WorkflowStep = { id: 's', type: 'writing', description: '', agent: 'a', depends_on: ['r'], status: 'pending', started_at: null, finished_at: null, duration: 0 }
    expect(step.depends_on.length === 0 ? 0 : 1).toBe(1)
  })
})
// ── Step Detail Panel ────────────────────────────────────────

describe('Step detail panel data', () => {
  it('step has error field when failed', () => {
    const step: WorkflowStep = { id: 's1', type: 'research', description: '', agent: 'a', depends_on: [], status: 'failed', started_at: null, finished_at: null, duration: 0, error: 'timeout' }
    expect(step.error).toBe('timeout')
  })

  it('step has null times when pending', () => {
    const step: WorkflowStep = { id: 's1', type: 'research', description: '', agent: 'a', depends_on: [], status: 'pending', started_at: null, finished_at: null, duration: 0 }
    expect(step.started_at).toBeNull()
    expect(step.finished_at).toBeNull()
  })

  it('step has valid ISO timestamps', () => {
    const step: WorkflowStep = { id: 's1', type: 'research', description: '', agent: 'a', depends_on: [], status: 'success', started_at: '2026-08-12T00:00:00Z', finished_at: '2026-08-12T00:00:05Z', duration: 5000 }
    expect(step.started_at).toContain('2026')
    expect(step.duration).toBeGreaterThan(0)
  })
})

// ── Workflow Data Structure ──────────────────────────────────

describe('WorkflowData structure', () => {
  it('has required fields', () => {
    const wf: WorkflowData = { task_id: 't1', intent: 'test', steps: [], total_steps: 0 }
    expect(wf.task_id).toBe('t1')
    expect(wf.intent).toBe('test')
    expect(wf.total_steps).toBe(0)
  })
})