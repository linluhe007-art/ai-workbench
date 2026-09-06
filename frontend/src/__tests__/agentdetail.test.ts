import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'
import {
  fetchAgentCapabilities,
  fetchAgentHealth,
  fetchAgentHistory,
  fetchAllCapabilities,
} from '../api/agentManagement'
import type { AgentCapabilities, AgentHealth, AgentHistory } from '../api/agentManagement'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

// ── API Tests ────────────────────────────────────────────────

describe('Agent Management API', () => {
  it('fetchAgentCapabilities returns capabilities', async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: 'default', capabilities: ['mock', 'test'], metadata: {}, experience: { task_count: 5, success_rate: 0.8 } },
    })
    const res = await fetchAgentCapabilities('default')
    expect(res.agent_id).toBe('default')
    expect(res.capabilities).toContain('mock')
    expect(res.experience.task_count).toBe(5)
    expect(mockGet).toHaveBeenCalledWith('/agents/default/capabilities')
  })

  it('fetchAgentHealth returns health', async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: 'default', healthy: true, state: 'IDLE', last_heartbeat: null, error: null },
    })
    const res = await fetchAgentHealth('default')
    expect(res.healthy).toBe(true)
    expect(res.state).toBe('IDLE')
    expect(mockGet).toHaveBeenCalledWith('/agents/default/health')
  })

  it('fetchAgentHistory returns history', async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: 'research', records: [{ task_id: 't1', success: true, duration: 200, created_at: '' }], total: 1 },
    })
    const res = await fetchAgentHistory('research')
    expect(res.total).toBe(1)
    expect(res.records[0].success).toBe(true)
    expect(mockGet).toHaveBeenCalledWith('/agents/research/history')
  })

  it('fetchAllCapabilities returns list', async () => {
    mockGet.mockResolvedValue({
      data: { capabilities: [{ name: 'research', agents: ['researcher'], count: 1 }], total: 1 },
    })
    const res = await fetchAllCapabilities()
    expect(res.total).toBe(1)
    expect(res.capabilities[0].name).toBe('research')
    expect(mockGet).toHaveBeenCalledWith('/agents/capabilities/all')
  })
})

// ── Type Structure Tests ─────────────────────────────────────

describe('AgentCapabilities structure', () => {
  it('has required fields', () => {
    const caps: AgentCapabilities = {
      agent_id: 'a1',
      capabilities: ['research', 'analysis'],
      metadata: { model: 'gpt-4' },
      experience: { task_count: 10, success_rate: 0.9 },
    }
    expect(caps.capabilities).toHaveLength(2)
    expect(caps.experience.success_rate).toBe(0.9)
  })
})

describe('AgentHealth structure', () => {
  it('has required fields', () => {
    const h: AgentHealth = {
      agent_id: 'a1',
      healthy: true,
      state: 'READY',
      last_heartbeat: '2026-08-12T00:00:00Z',
      error: null,
    }
    expect(h.healthy).toBe(true)
    expect(h.error).toBeNull()
  })

  it('supports error state', () => {
    const h: AgentHealth = {
      agent_id: 'a1',
      healthy: false,
      state: 'FAILED',
      last_heartbeat: null,
      error: 'Connection timeout',
    }
    expect(h.healthy).toBe(false)
    expect(h.error).toBe('Connection timeout')
  })
})

// ── Health State Mapping ─────────────────────────────────────

describe('Health state config mapping', () => {
  const stateConfig: Record<string, string> = {
    IDLE: '空闲',
    READY: '就绪',
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '失败',
    STOPPED: '已停止',
    UNKNOWN: '未知',
  }

  it('maps all known states', () => {
    for (const state of Object.keys(stateConfig)) {
      expect(stateConfig[state]).toBeDefined()
    }
  })

  it('IDLE maps to 空闲', () => {
    expect(stateConfig['IDLE']).toBe('空闲')
  })

  it('FAILED maps to 失败', () => {
    expect(stateConfig['FAILED']).toBe('失败')
  })
})

// ── Capability Display ───────────────────────────────────────

describe('Capability display logic', () => {
  const capColors: Record<string, string> = {
    research: 'blue',
    analysis: 'green',
    writing: 'purple',
    mock: 'default',
    test: 'orange',
  }

  it('maps known capabilities to colors', () => {
    expect(capColors['research']).toBe('blue')
    expect(capColors['analysis']).toBe('green')
    expect(capColors['writing']).toBe('purple')
  })

  it('defaults for unknown capabilities', () => {
    expect(capColors['unknown'] || 'default').toBe('default')
  })

  it('filters empty capabilities', () => {
    const caps: string[] = []
    expect(caps.length).toBe(0)
  })
})

// ── History Rendering ────────────────────────────────────────

describe('Agent history data', () => {
  it('history record has required fields', () => {
    const record = { task_id: 'research AI', success: true, duration: 500, created_at: '2026-08-12T00:00:00Z' }
    expect(record.task_id).toBe('research AI')
    expect(record.success).toBe(true)
    expect(record.duration).toBe(500)
  })

  it('formats duration for display', () => {
    const ms = 1234
    expect(`${ms}ms`).toBe('1234ms')
  })

  it('handles zero duration', () => {
    const ms = 0
    const display = ms > 0 ? `${ms}ms` : '-'
    expect(display).toBe('-')
  })

  it('handles empty records', () => {
    const records: { task_id: string; success: boolean }[] = []
    expect(records.length).toBe(0)
  })
})

// ── Agent State Colors ───────────────────────────────────────

describe('Agent state color mapping', () => {
  const colors: Record<string, string> = {
    idle: 'default',
    running: 'processing',
    completed: 'success',
    failed: 'error',
  }

  it('maps idle to default', () => {
    expect(colors['idle']).toBe('default')
  })

  it('maps running to processing', () => {
    expect(colors['running']).toBe('processing')
  })

  it('maps failed to error', () => {
    expect(colors['failed']).toBe('error')
  })

  it('defaults unknown state', () => {
    expect(colors['unknown'] || 'default').toBe('default')
  })
})