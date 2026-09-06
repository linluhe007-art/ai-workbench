import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useTasks, useCreateTask } from '../hooks/useTasks'
import { useAgents, useMetrics } from '../hooks/useAgents'
import apiClient from '../api/client'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => vi.clearAllMocks())

describe('useTasks', () => {
  it('fetches tasks', async () => {
    mockGet.mockResolvedValue({ data: { tasks: [{ task_id: 't1', task: 'test', status: 'pending' }] } })
    const { result } = renderHook(() => useTasks(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(1)
  })
})

describe('useAgents', () => {
  it('fetches agents', async () => {
    mockGet.mockResolvedValue({ data: { agents: [], total: 0 } })
    const { result } = renderHook(() => useAgents(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(0)
  })
})

describe('useMetrics', () => {
  it('fetches metrics', async () => {
    mockGet.mockResolvedValue({ data: { total_tasks: 3, success_rate: 0.9, average_duration_ms: 100 } })
    const { result } = renderHook(() => useMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_tasks).toBe(3)
  })
})

describe('useCreateTask', () => {
  it('creates task and invalidates cache', async () => {
    mockPost.mockResolvedValue({ data: { task_id: 't1', task: 'test', status: 'pending' } })
    const { result } = renderHook(() => useCreateTask(), { wrapper })
    result.current.mutate({ task: 'test' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.task_id).toBe('t1')
  })
})