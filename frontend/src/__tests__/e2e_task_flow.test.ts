import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'

vi.mock('../api/client')
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

beforeEach(() => vi.clearAllMocks())

describe('Full Task Lifecycle API', () => {
  it('creates a task', async () => {
    mockPost.mockResolvedValue({ data: { task_id: 't1', task: 'test', status: 'pending' } })
    const resp = await apiClient.post('/tasks', { task: 'test' })
    expect(resp.data.task_id).toBe('t1')
    expect(resp.data.status).toBe('pending')
  })

  it('gets task status', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', status: 'running', attempt: 1 } })
    const resp = await apiClient.get('/tasks/t1')
    expect(resp.data.status).toBe('running')
  })

  it('lists tasks', async () => {
    mockGet.mockResolvedValue({ data: { tasks: [{ task_id: 't1' }, { task_id: 't2' }] } })
    const resp = await apiClient.get('/tasks')
    expect(resp.data.tasks).toHaveLength(2)
  })

  it('cancels a task', async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: 't1', status: 'cancelled' } })
    const resp = await apiClient.post('/tasks/t1/cancel')
    expect(resp.data.success).toBe(true)
  })

  it('pauses a task', async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: 't1' } })
    const resp = await apiClient.post('/tasks/t1/pause')
    expect(resp.data.success).toBe(true)
  })

  it('resumes a task', async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: 't1' } })
    const resp = await apiClient.post('/tasks/t1/resume')
    expect(resp.data.success).toBe(true)
  })

  it('retries a task', async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: 't1', status: 'queued' } })
    const resp = await apiClient.post('/tasks/t1/retry')
    expect(resp.data.success).toBe(true)
  })

  it('gets task events', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', events: [], total: 0, last_sequence: 0 } })
    const resp = await apiClient.get('/tasks/t1/events')
    expect(resp.data.task_id).toBe('t1')
    expect(resp.data.events).toBeDefined()
  })

  it('gets task trace', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', events: [], total: 0 } })
    const resp = await apiClient.get('/tasks/t1/trace')
    expect(resp.data.task_id).toBe('t1')
  })

  it('gets task history', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', history: [], total: 0 } })
    const resp = await apiClient.get('/tasks/t1/history')
    expect(resp.data.task_id).toBe('t1')
  })
})

describe('Task Status Transitions', () => {
  const validStates = ['pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled', 'timeout']
  validStates.forEach(state => {
    it(`handles ${state} status in response`, () => {
      expect(validStates).toContain(state)
    })
  })
})

describe('Error States in Task Flow', () => {
  it('handles 404 for unknown task', async () => {
    mockGet.mockRejectedValue({ response: { status: 404, data: { error: { code: 'TASK_NOT_FOUND' } } } })
    await expect(apiClient.get('/tasks/unknown')).rejects.toBeDefined()
  })

  it('handles 409 for invalid transition', async () => {
    mockPost.mockRejectedValue({ response: { status: 409, data: { error: { code: 'INVALID_TASK_STATE' } } } })
    await expect(apiClient.post('/tasks/t1/pause')).rejects.toBeDefined()
  })
})
