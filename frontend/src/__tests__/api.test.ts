import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'
import { fetchTasks, createTask, fetchTask, fetchTaskTrace } from '../api/tasks'
import { fetchAgents, fetchMetrics, fetchRuntimeStatus } from '../api/agents'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Tasks API', () => {
  it('fetchTasks returns task list', async () => {
    mockGet.mockResolvedValue({ data: { tasks: [{ task_id: 't1', task: 'test', status: 'pending' }] } })
    const tasks = await fetchTasks()
    expect(tasks).toHaveLength(1)
    expect(tasks[0].task_id).toBe('t1')
    expect(mockGet).toHaveBeenCalledWith('/tasks')
  })

  it('createTask posts and returns response', async () => {
    mockPost.mockResolvedValue({ data: { task_id: 't1', task: 'test', status: 'pending' } })
    const res = await createTask({ task: 'test' })
    expect(res.task_id).toBe('t1')
    expect(mockPost).toHaveBeenCalledWith('/tasks', { task: 'test' })
  })

  it('fetchTask returns single task', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', task: 'test', status: 'completed' } })
    const task = await fetchTask('t1')
    expect(task.task_id).toBe('t1')
    expect(mockGet).toHaveBeenCalledWith('/tasks/t1')
  })

  it('fetchTaskTrace returns trace data', async () => {
    mockGet.mockResolvedValue({ data: { task_id: 't1', events: [], total: 0 } })
    const trace = await fetchTaskTrace('t1')
    expect(trace.total).toBe(0)
    expect(mockGet).toHaveBeenCalledWith('/tasks/t1/trace')
  })
})

describe('Agents API', () => {
  it('fetchAgents returns agent list', async () => {
    mockGet.mockResolvedValue({ data: { agents: [{ id: 'default', state: 'idle' }], total: 1 } })
    const res = await fetchAgents()
    expect(res.total).toBe(1)
    expect(res.agents[0].id).toBe('default')
    expect(mockGet).toHaveBeenCalledWith('/agents')
  })

  it('fetchMetrics returns metrics', async () => {
    mockGet.mockResolvedValue({ data: { total_tasks: 5, success_rate: 0.8, average_duration_ms: 200 } })
    const m = await fetchMetrics()
    expect(m.total_tasks).toBe(5)
    expect(mockGet).toHaveBeenCalledWith('/executions/metrics')
  })

  it('fetchRuntimeStatus returns status', async () => {
    mockGet.mockResolvedValue({ data: { agents_count: 4, tasks_count: 2, metrics: {} } })
    const s = await fetchRuntimeStatus()
    expect(s.agents_count).toBe(4)
    expect(mockGet).toHaveBeenCalledWith('/agents/status/runtime')
  })
})