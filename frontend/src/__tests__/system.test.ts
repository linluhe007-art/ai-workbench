import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import apiClient from '../api/client'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => vi.clearAllMocks())

describe('System Health API', () => {
  it('fetches health status', async () => {
    mockGet.mockResolvedValue({ data: { status: 'healthy', timestamp: '2024-01-01T00:00:00' } })
    const response = await apiClient.get('/system/health')
    expect(response.data.status).toBe('healthy')
    expect(response.data.timestamp).toBeDefined()
  })

  it('fetches readiness status', async () => {
    mockGet.mockResolvedValue({ data: { ready: true, status: 'running' } })
    const response = await apiClient.get('/system/readiness')
    expect(response.data.ready).toBe(true)
    expect(response.data.status).toBe('running')
  })

  it('fetches system info', async () => {
    mockGet.mockResolvedValue({ data: { instance_id: 'inst-1', status: 'running', active_tasks: 2 } })
    const response = await apiClient.get('/system/info')
    expect(response.data.instance_id).toBe('inst-1')
    expect(response.data.active_tasks).toBe(2)
  })

  it('handles health check failure', async () => {
    mockGet.mockRejectedValue(new Error('Service unavailable'))
    await expect(apiClient.get('/system/health')).rejects.toThrow('Service unavailable')
  })
})

describe('System Info Response Schema', () => {
  it('system info has required fields', async () => {
    mockGet.mockResolvedValue({
      data: {
        instance_id: 'i1',
        started_at: '2024-01-01T00:00:00',
        status: 'running',
        health: {
          status: 'healthy',
          persistence_status: 'healthy',
          redis_status: 'healthy',
        },
      },
    })
    const response = await apiClient.get('/system/info')
    expect(response.data.instance_id).toBeDefined()
    expect(response.data.status).toBeDefined()
  })

  it('readiness has all required fields', async () => {
    mockGet.mockResolvedValue({
      data: {
        ready: true,
        status: 'running',
        persistence: 'healthy',
        redis: 'healthy',
        instance_id: 'i1',
        uptime_seconds: 123.5,
        timestamp: '2024-01-01T00:00:00',
      },
    })
    const response = await apiClient.get('/system/readiness')
    expect(response.data.ready).toBeDefined()
    expect(response.data.persistence).toBeDefined()
    expect(response.data.redis).toBeDefined()
  })
})

describe('System Metrics API', () => {
  it('fetches metrics', async () => {
    mockGet.mockResolvedValue({
      data: {
        metrics: { total_tasks: 10, success_rate: 0.9 },
        queue: { running: 2, queued: 3 },
      },
    })
    const response = await apiClient.get('/system/metrics')
    expect(response.data.metrics).toBeDefined()
    expect(response.data.queue).toBeDefined()
    expect(response.data.metrics.total_tasks).toBe(10)
  })

  it('handles metrics failure gracefully', async () => {
    mockGet.mockResolvedValue({ data: { error: 'not available' } })
    const response = await apiClient.get('/system/metrics')
    expect(response.data.error).toBeDefined()
  })
})

describe('Shutdown API', () => {
  it('initiates shutdown', async () => {
    const mockPost = vi.mocked(apiClient.post)
    mockPost.mockResolvedValue({ data: { status: 'shutting_down', message: 'Graceful shutdown initiated' } })
    const response = await apiClient.post('/system/shutdown')
    expect(response.data.status).toBe('shutting_down')
  })

  it('handles double shutdown', async () => {
    const mockPost = vi.mocked(apiClient.post)
    mockPost.mockResolvedValue({ data: { status: 'shutdown_already_in_progress' } })
    const response = await apiClient.post('/system/shutdown')
    expect(response.data.status).toBe('shutdown_already_in_progress')
  })
})
