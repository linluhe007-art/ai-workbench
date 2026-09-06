import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TaskWsClient } from '../websocket/client'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onmessage: ((msg: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  sent: string[] = []
  closed = false

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }
  send(data: string) { this.sent.push(data) }
  close() { this.closed = true }
}

describe('TaskWsClient event handling', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:5173' } })
  })

  it('handles task_started event', () => {
    const client = new TaskWsClient('t1')
    const handler = vi.fn()
    client.on('task_started', handler)
    client.connect()
    MockWebSocket.instances[0].onmessage!({
      data: JSON.stringify({ event: 'task_started', task_id: 't1', timestamp: '', data: {} }),
    })
    expect(handler).toHaveBeenCalledTimes(1)
    client.close()
  })

  it('handles agent_started event', () => {
    const client = new TaskWsClient('t1')
    const handler = vi.fn()
    client.on('agent_started', handler)
    client.connect()
    MockWebSocket.instances[0].onmessage!({
      data: JSON.stringify({ event: 'agent_started', task_id: 't1', timestamp: '', data: { agent_id: 'research' } }),
    })
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ event: 'agent_started' }))
    client.close()
  })

  it('handles task_failed event', () => {
    const client = new TaskWsClient('t1')
    const handler = vi.fn()
    client.on('task_failed', handler)
    client.connect()
    MockWebSocket.instances[0].onmessage!({
      data: JSON.stringify({ event: 'task_failed', task_id: 't1', timestamp: '', data: { error: 'timeout' } }),
    })
    expect(handler).toHaveBeenCalledTimes(1)
    expect(handler.mock.calls[0][0].data.error).toBe('timeout')
    client.close()
  })

  it('handles evaluation_updated event', () => {
    const client = new TaskWsClient('t1')
    const handler = vi.fn()
    client.on('evaluation_updated', handler)
    client.connect()
    MockWebSocket.instances[0].onmessage!({
      data: JSON.stringify({ event: 'evaluation_updated', task_id: 't1', timestamp: '', data: { score: 8.5 } }),
    })
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ data: { score: 8.5 } }))
    client.close()
  })

  it('multiple handlers for same event', () => {
    const client = new TaskWsClient('t1')
    const h1 = vi.fn()
    const h2 = vi.fn()
    client.on('step_completed', h1)
    client.on('step_completed', h2)
    client.connect()
    MockWebSocket.instances[0].onmessage!({
      data: JSON.stringify({ event: 'step_completed', task_id: 't1', timestamp: '', data: {} }),
    })
    expect(h1).toHaveBeenCalledTimes(1)
    expect(h2).toHaveBeenCalledTimes(1)
    client.close()
  })

  it('wildcard catches all events', () => {
    const client = new TaskWsClient('t1')
    const wildcard = vi.fn()
    client.on('*', wildcard)
    client.connect()
    for (const evt of ['task_started', 'agent_started', 'task_completed']) {
      MockWebSocket.instances[0].onmessage!({
        data: JSON.stringify({ event: evt, task_id: 't1', timestamp: '', data: {} }),
      })
    }
    expect(wildcard).toHaveBeenCalledTimes(3)
    client.close()
  })

  it('URL construction with task id', () => {
    const client = new TaskWsClient('task-abc-123')
    client.connect()
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:5173/api/v1/ws/tasks/task-abc-123')
    client.close()
  })

  it('cleanup on close', () => {
    const client = new TaskWsClient('t1')
    client.connect()
    expect(MockWebSocket.instances[0].closed).toBe(false)
    client.close()
    expect(MockWebSocket.instances[0].closed).toBe(true)
  })
})