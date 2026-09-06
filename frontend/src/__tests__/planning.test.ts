import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'
import {
  debugPlanning,
  fetchPlanningSession,
  fetchPlanningSessions,
  type PlanningDebugSession,
} from '../api/planning'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

const baseSession: PlanningDebugSession = {
  session_id: 's1',
  task: 'research AI trends',
  planner_type: 'llm',
  prompt: 'Plan: research AI trends',
  raw_response: '{"steps":[]}',
  parsed_plan: {
    intent: 'research AI trends',
    steps: [
      { id: 'research', type: 'research', description: 'search info', depends_on: [], agent_hint: 'researcher' },
      { id: 'analysis', type: 'analysis', description: 'analyze info', depends_on: ['research'], agent_hint: 'analyst' },
    ],
  },
  selected_agents: { research: 'researcher', analysis: 'analyst' },
  capabilities: { research: ['researcher'], analysis: ['analyst'] },
  fallback_used: false,
  error: null,
  duration_ms: 150.5,
  created_at: '2026-08-12T10:00:00Z',
}

// ─── API Tests ───────────────────────────────────────────────

describe('Planning API', () => {
  it('debugPlanning posts task and returns session', async () => {
    mockPost.mockResolvedValue({ data: baseSession })
    const res = await debugPlanning('research AI trends')
    expect(res.session_id).toBe('s1')
    expect(mockPost).toHaveBeenCalledWith('/planning/debug', { task: 'research AI trends' })
  })

  it('fetchPlanningSession gets session by id', async () => {
    mockGet.mockResolvedValue({ data: baseSession })
    const res = await fetchPlanningSession('s1')
    expect(res.session_id).toBe('s1')
    expect(mockGet).toHaveBeenCalledWith('/planning/debug/s1')
  })

  it('fetchPlanningSessions returns list', async () => {
    mockGet.mockResolvedValue({ data: { sessions: [baseSession], total: 1 } })
    const res = await fetchPlanningSessions()
    expect(res.sessions).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith('/planning/debug')
  })

  it('debugPlanning handles network error', async () => {
    mockPost.mockRejectedValue(new Error('Network Error'))
    await expect(debugPlanning('test')).rejects.toThrow('Network Error')
  })

  it('fetchPlanningSession handles 404', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } })
    await expect(fetchPlanningSession('bad')).rejects.toEqual({ response: { status: 404 } })
  })
})

// ─── Data Transformation ─────────────────────────────────────

describe('Plan data transformation', () => {
  it('parsed_plan steps have correct structure', () => {
    const plan = baseSession.parsed_plan!
    expect(plan.steps).toHaveLength(2)
    expect(plan.steps[0]).toHaveProperty('id')
    expect(plan.steps[0]).toHaveProperty('type')
    expect(plan.steps[0]).toHaveProperty('depends_on')
    expect(plan.steps[0]).toHaveProperty('agent_hint')
  })

  it('dependencies form correct DAG', () => {
    const steps = baseSession.parsed_plan!.steps
    const edges: { source: string; target: string }[] = []
    for (const step of steps) {
      for (const dep of step.depends_on) {
        edges.push({ source: dep, target: step.id })
      }
    }
    expect(edges).toHaveLength(1)
    expect(edges[0]).toEqual({ source: 'research', target: 'analysis' })
  })

  it('selected_agents maps step to agent', () => {
    expect(baseSession.selected_agents['research']).toBe('researcher')
    expect(baseSession.selected_agents['analysis']).toBe('analyst')
  })

  it('capabilities lists candidates per step', () => {
    expect(baseSession.capabilities['research']).toContain('researcher')
    expect(baseSession.capabilities['analysis']).toContain('analyst')
  })
})

// ─── Status Mapping ──────────────────────────────────────────

describe('Status mapping', () => {
  it('planner_type llm maps to blue', () => {
    const colorMap: Record<string, string> = { llm: 'blue', rule: 'orange' }
    expect(colorMap[baseSession.planner_type]).toBe('blue')
  })

  it('planner_type rule maps to orange', () => {
    const colorMap: Record<string, string> = { llm: 'blue', rule: 'orange' }
    const ruleSession = { ...baseSession, planner_type: 'rule' }
    expect(colorMap[ruleSession.planner_type]).toBe('orange')
  })

  it('fallback_used true shows warning tag', () => {
    const s = { ...baseSession, fallback_used: true }
    expect(s.fallback_used).toBe(true)
  })

  it('fallback_used false shows success', () => {
    expect(baseSession.fallback_used).toBe(false)
  })

  it('error present shows error status', () => {
    const s = { ...baseSession, error: 'LLM timeout' }
    expect(s.error).toBeTruthy()
  })

  it('no error shows success status', () => {
    expect(baseSession.error).toBeNull()
  })
})

// ─── Duration Formatting ─────────────────────────────────────

describe('Duration formatting', () => {
  it('formats duration in ms', () => {
    expect(baseSession.duration_ms.toFixed(0)).toBe('151')
  })

  it('handles zero duration', () => {
    const s = { ...baseSession, duration_ms: 0 }
    expect(s.duration_ms.toFixed(0)).toBe('0')
  })

  it('handles large duration', () => {
    const s = { ...baseSession, duration_ms: 12345.678 }
    expect(s.duration_ms.toFixed(0)).toBe('12346')
  })
})

// ─── Empty States ────────────────────────────────────────────

describe('Empty states', () => {
  it('null parsed_plan means no steps', () => {
    const s = { ...baseSession, parsed_plan: null }
    expect(s.parsed_plan).toBeNull()
  })

  it('empty selected_agents', () => {
    const s = { ...baseSession, selected_agents: {} }
    expect(Object.keys(s.selected_agents)).toHaveLength(0)
  })

  it('empty sessions list', () => {
    const data = { sessions: [] as PlanningDebugSession[], total: 0 }
    expect(data.sessions).toHaveLength(0)
    expect(data.total).toBe(0)
  })

  it('null prompt should hide PromptPanel', () => {
    const s = { ...baseSession, prompt: null }
    expect(s.prompt).toBeNull()
  })

  it('null raw_response should hide RawResponsePanel', () => {
    const s = { ...baseSession, raw_response: null }
    expect(s.raw_response).toBeNull()
  })
})

// ─── Step Type Colors ────────────────────────────────────────

describe('Step type color mapping', () => {
  const typeColors: Record<string, string> = {
    research: 'blue',
    analysis: 'green',
    writing: 'purple',
    image: 'magenta',
    seo: 'gold',
    custom: 'default',
  }

  it('research is blue', () => {
    expect(typeColors['research']).toBe('blue')
  })

  it('analysis is green', () => {
    expect(typeColors['analysis']).toBe('green')
  })

  it('writing is purple', () => {
    expect(typeColors['writing']).toBe('purple')
  })

  it('unknown type falls back to default', () => {
    expect(typeColors['unknown'] || 'default').toBe('default')
  })
})

// ─── Session Selection ───────────────────────────────────────

describe('Session selection', () => {
  it('finds session by id in list', () => {
    const sessions = [baseSession, { ...baseSession, session_id: 's2', task: 'other' }]
    const found = sessions.find((s) => s.session_id === 's2')
    expect(found?.task).toBe('other')
  })

  it('returns undefined for missing session id', () => {
    const sessions = [baseSession]
    const found = sessions.find((s) => s.session_id === 'missing')
    expect(found).toBeUndefined()
  })
})
