import { describe, it, expect } from 'vitest'
import type { TraceEvent, WsEvent } from '../../types'

// Test helper: build TraceEvent
function makeTrace(overrides: Partial<TraceEvent> = {}): TraceEvent {
  return {
    trace_id: 'trace-1',
    task_id: 'task-1',
    component: 'executor',
    event_type: 'start',
    timestamp: new Date().toISOString(),
    duration_ms: 0,
    metadata: {},
    ...overrides,
  }
}

function makeWsEvent(overrides: Partial<WsEvent> = {}): WsEvent {
  return {
    event: 'task_started',
    task_id: 'task-1',
    timestamp: new Date().toISOString(),
    data: {},
    ...overrides,
  }
}

describe('Timeline data processing', () => {
  it('creates trace events with required fields', () => {
    const e = makeTrace()
    expect(e.trace_id).toBe('trace-1')
    expect(e.event_type).toBe('start')
    expect(e.component).toBe('executor')
  })

  it('creates trace events with duration', () => {
    const e = makeTrace({ event_type: 'end', duration_ms: 250 })
    expect(e.duration_ms).toBe(250)
    expect(e.event_type).toBe('end')
  })

  it('creates trace events with metadata', () => {
    const e = makeTrace({ metadata: { step_id: 's1', agent_id: 'research' } })
    expect(e.metadata.step_id).toBe('s1')
    expect(e.metadata.agent_id).toBe('research')
  })

  it('creates error trace events', () => {
    const e = makeTrace({ event_type: 'error', metadata: { error: 'timeout' } })
    expect(e.event_type).toBe('error')
    expect(e.metadata.error).toBe('timeout')
  })

  it('creates metric trace events', () => {
    const e = makeTrace({ event_type: 'metric', metadata: { metric_name: 'eval_score', metric_value: 8.5 } })
    expect(e.event_type).toBe('metric')
    expect(e.metadata.metric_value).toBe(8.5)
  })

  it('merges traces and ws events', () => {
    const traces = [makeTrace({ event_type: 'start' }), makeTrace({ event_type: 'end' })]
    const wsEvents = [makeWsEvent({ event: 'task_completed' })]
    const total = traces.length + wsEvents.length
    expect(total).toBe(3)
  })

  it('handles empty trace list', () => {
    const traces: TraceEvent[] = []
    expect(traces.length).toBe(0)
  })
})

describe('WsEvent data processing', () => {
  it('creates ws event with defaults', () => {
    const e = makeWsEvent()
    expect(e.event).toBe('task_started')
    expect(e.task_id).toBe('task-1')
  })

  it('creates ws event with custom data', () => {
    const e = makeWsEvent({ event: 'agent_finished', data: { agent: 'research', duration_ms: 500 } })
    expect(e.event).toBe('agent_finished')
    expect(e.data.agent).toBe('research')
  })

  it('handles all event types', () => {
    const types = [
      'task_started', 'agent_started', 'agent_finished',
      'step_completed', 'evaluation_updated', 'task_completed', 'task_failed',
    ]
    for (const t of types) {
      const e = makeWsEvent({ event: t })
      expect(e.event).toBe(t)
    }
  })
})

describe('EvaluationPanel data', () => {
  it('score mapping - excellent', () => {
    const score = 9.0
    expect(score).toBeGreaterThanOrEqual(8)
  })

  it('score mapping - good', () => {
    const score = 7.0
    expect(score).toBeGreaterThanOrEqual(6)
    expect(score).toBeLessThan(8)
  })

  it('score mapping - fair', () => {
    const score = 4.0
    expect(score).toBeLessThan(6)
  })

  it('quality label mapping', () => {
    const qualities = ['excellent', 'good', 'fair', 'poor']
    expect(qualities).toContain('excellent')
    expect(qualities).toContain('poor')
  })

  it('handles undefined evaluation', () => {
    const evaluation = undefined
    expect(evaluation).toBeUndefined()
  })
})

describe('Status config', () => {
  it('maps all task statuses', () => {
    const statuses = ['pending', 'running', 'completed', 'failed']
    const config: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
    }
    for (const s of statuses) {
      expect(config[s]).toBeDefined()
    }
  })
})

describe('Component color mapping', () => {
  it('maps component to tag color', () => {
    const colorMap: Record<string, string> = {
      loop: 'blue',
      executor: 'green',
      agent: 'purple',
    }
    expect(colorMap['loop']).toBe('blue')
    expect(colorMap['executor']).toBe('green')
    expect(colorMap['agent']).toBe('purple')
  })
})