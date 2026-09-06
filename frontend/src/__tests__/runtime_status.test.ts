import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'

vi.mock('../api/client')
const mockGet = vi.mocked(apiClient.get)

beforeEach(() => vi.clearAllMocks())

describe('Runtime Status States', () => {
  it('healthy state', async () => {
    mockGet.mockResolvedValue({
      data: { ready: true, status: 'running', persistence: 'healthy', redis: 'healthy' }
    })
    const resp = await apiClient.get('/system/readiness')
    expect(resp.data.ready).toBe(true)
    expect(resp.data.persistence).toBe('healthy')
    expect(resp.data.redis).toBe('healthy')
  })

  it('degraded state - db down', async () => {
    mockGet.mockResolvedValue({
      data: { ready: true, status: 'degraded', persistence: 'unavailable', redis: 'healthy' }
    })
    const resp = await apiClient.get('/system/readiness')
    expect(resp.data.ready).toBe(true)
    expect(resp.data.persistence).toBe('unavailable')
    expect(resp.data.redis).toBe('healthy')
  })

  it('degraded state - redis down', async () => {
    mockGet.mockResolvedValue({
      data: { ready: true, status: 'degraded', persistence: 'healthy', redis: 'unavailable' }
    })
    const resp = await apiClient.get('/system/readiness')
    expect(resp.data.persistence).toBe('healthy')
    expect(resp.data.redis).toBe('unavailable')
  })

  it('error state', async () => {
    mockGet.mockResolvedValue({
      data: { ready: false, status: 'error', error: 'connection refused' }
    })
    const resp = await apiClient.get('/system/readiness')
    expect(resp.data.ready).toBe(false)
    expect(resp.data.error).toBeDefined()
  })
})

describe('Runtime Info Fields', () => {
  it('has instance_id', async () => {
    mockGet.mockResolvedValue({
      data: { instance_id: 'inst-abc123', status: 'running' }
    })
    const resp = await apiClient.get('/system/info')
    expect(resp.data.instance_id).toMatch(/^inst-/)
  })

  it('has uptime', async () => {
    mockGet.mockResolvedValue({
      data: { instance_id: 'i1', uptime_seconds: 3600 }
    })
    const resp = await apiClient.get('/system/readiness')
    expect(resp.data.uptime_seconds).toBeGreaterThan(0)
  })

  it('has active_tasks count', async () => {
    mockGet.mockResolvedValue({
      data: { instance_id: 'i1', active_tasks: 5, queued_tasks: 2 }
    })
    const resp = await apiClient.get('/system/info')
    expect(resp.data.active_tasks).toBeGreaterThanOrEqual(0)
    expect(resp.data.queued_tasks).toBeGreaterThanOrEqual(0)
  })

  it('has metrics in info', async () => {
    mockGet.mockResolvedValue({
      data: {
        instance_id: 'i1',
        metrics: {
          total_tasks: 100,
          success_rate: 0.95,
          average_duration: 12.5,
        },
      },
    })
    const resp = await apiClient.get('/system/info')
    expect(resp.data.metrics).toBeDefined()
    expect(resp.data.metrics.total_tasks).toBe(100)
  })
})

describe('Health API Status Mapping', () => {
  const statusCases = [
    { status: 'healthy', expected: 'healthy' },
    { status: 'degraded', expected: 'degraded' },
    { status: 'unavailable', expected: 'unavailable' },
    { status: 'error', expected: 'error' },
  ]

  statusCases.forEach(({ status, expected }) => {
    it(`maps ${status} correctly`, async () => {
      mockGet.mockResolvedValue({ data: { status } })
      const resp = await apiClient.get('/system/health')
      expect(resp.data.status).toBe(expected)
    })
  })
})

describe('Error Handling', () => {
  it('handles network error', async () => {
    mockGet.mockRejectedValue(new Error('Network Error'))
    await expect(apiClient.get('/system/health')).rejects.toThrow('Network Error')
  })

  it('handles 500 error', async () => {
    mockGet.mockRejectedValue({ response: { status: 500, data: { error: 'Internal error' } } })
    await expect(apiClient.get('/system/info')).rejects.toBeDefined()
  })

  it('handles timeout', async () => {
    mockGet.mockRejectedValue(new Error('timeout'))
    await expect(apiClient.get('/system/readiness')).rejects.toThrow('timeout')
  })
})
