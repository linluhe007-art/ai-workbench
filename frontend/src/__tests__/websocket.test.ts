import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TaskWsClient } from '../websocket/client'

// Mock WebSocket
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

describe('TaskWsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:5173' } })
  })

  it('constructs with correct URL', () => {
    const client = new TaskWsClient('task-123')
    client.connect()
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:5173/api/v1/ws/tasks/task-123')
    client.close()
  })

  it('dispatches events to handlers', () => {
    const client = new TaskWsClient('task-1')
    const handler = vi.fn()
    client.on('task_completed', handler)
    client.connect()

    // Simulate message
    const ws = MockWebSocket.instances[0]
    ws.onmessage!({ data: JSON.stringify({ event: 'task_completed', task_id: 'task-1', timestamp: '', data: {} }) })

    expect(handler).toHaveBeenCalledTimes(1)
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ event: 'task_completed' }))
    client.close()
  })

  it('dispatches to wildcard handlers', () => {
    const client = new TaskWsClient('task-1')
    const handler = vi.fn()
    client.on('*', handler)
    client.connect()

    const ws = MockWebSocket.instances[0]
    ws.onmessage!({ data: JSON.stringify({ event: 'any_event', task_id: 'task-1', timestamp: '', data: {} }) })

    expect(handler).toHaveBeenCalledTimes(1)
    client.close()
  })

  it('removes handler on off()', () => {
    const client = new TaskWsClient('task-1')
    const handler = vi.fn()
    client.on('test', handler)
    client.off('test', handler)
    client.connect()

    const ws = MockWebSocket.instances[0]
    ws.onmessage!({ data: JSON.stringify({ event: 'test', task_id: 'task-1', timestamp: '', data: {} }) })

    expect(handler).not.toHaveBeenCalled()
    client.close()
  })

  it('sends ping', () => {
    const client = new TaskWsClient('task-1')
    client.connect()
    client.ping()
    expect(MockWebSocket.instances[0].sent).toContain('ping')
    client.close()
  })

  it('close stops reconnection', () => {
    const client = new TaskWsClient('task-1')
    client.connect()
    client.close()
    expect(MockWebSocket.instances[0].closed).toBe(true)
  })

  it('ignores malformed messages', () => {
    const client = new TaskWsClient('task-1')
    const handler = vi.fn()
    client.on('test', handler)
    client.connect()

    const ws = MockWebSocket.instances[0]
    // Should not throw
    ws.onmessage!({ data: 'not json' })
    expect(handler).not.toHaveBeenCalled()
    client.close()
  })
})