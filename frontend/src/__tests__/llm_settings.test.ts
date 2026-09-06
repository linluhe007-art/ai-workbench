import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { fetchLLMConfig, testLLM } from '../api/llm'
import { useLLMConfig, useLLMTest } from '../hooks/useLLM'
import apiClient from '../api/client'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const configResponse = {
  provider: 'deepseek',
  model: 'deepseek-chat',
  configured: true,
  api_key_set: true,
  supported_providers: ['deepseek', 'openai', 'mock'],
}

beforeEach(() => vi.clearAllMocks())

describe('LLM API client', () => {
  it('fetchLLMConfig requests /llm/config', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.provider).toBe('deepseek')
    expect(mockGet).toHaveBeenCalledWith('/llm/config')
  })

  it('fetchLLMConfig returns model name', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.model).toBe('deepseek-chat')
  })

  it('fetchLLMConfig exposes configured flag', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.configured).toBe(true)
  })

  it('fetchLLMConfig exposes supported providers', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.supported_providers).toHaveLength(3)
  })

  it('testLLM posts prompt and returns content', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'ok', model: 'deepseek-chat', input_tokens: 5, output_tokens: 2, latency_ms: 100, finish_reason: 'stop' },
    })
    const res = await testLLM({ prompt: 'hello' })
    expect(res.success).toBe(true)
    expect(res.content).toBe('ok')
    expect(mockPost).toHaveBeenCalledWith('/llm/test', { prompt: 'hello' })
  })

  it('testLLM includes model override when provided', async () => {
    mockPost.mockResolvedValue({ data: { success: true, content: '', model: 'deepseek-reasoner' } })
    await testLLM({ prompt: 'x', model: 'deepseek-reasoner' })
    expect(mockPost).toHaveBeenCalledWith('/llm/test', { prompt: 'x', model: 'deepseek-reasoner' })
  })

  it('testLLM includes temperature and max tokens', async () => {
    mockPost.mockResolvedValue({ data: { success: true, content: '', model: 'deepseek-chat' } })
    await testLLM({ prompt: 'x', temperature: 0.5, max_tokens: 100 })
    expect(mockPost).toHaveBeenCalledWith('/llm/test', { prompt: 'x', temperature: 0.5, max_tokens: 100 })
  })

  it('testLLM returns token counts', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'a', model: 'deepseek-chat', input_tokens: 3, output_tokens: 4, latency_ms: 20, finish_reason: 'stop' },
    })
    const res = await testLLM({ prompt: 'a' })
    expect(res.input_tokens).toBe(3)
    expect(res.output_tokens).toBe(4)
  })

  it('testLLM returns latency', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'a', model: 'deepseek-chat', input_tokens: 1, output_tokens: 1, latency_ms: 55, finish_reason: 'stop' },
    })
    const res = await testLLM({ prompt: 'a' })
    expect(res.latency_ms).toBe(55)
  })
})

describe('useLLMConfig hook', () => {
  it('loads config', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const { result } = renderHook(() => useLLMConfig(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.provider).toBe('deepseek')
  })

  it('tracks loading state', async () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useLLMConfig(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it('exposes configured state', async () => {
    mockGet.mockResolvedValue({ data: { ...configResponse, configured: false, api_key_set: false } })
    const { result } = renderHook(() => useLLMConfig(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.configured).toBe(false)
  })

  it('exposes error state', async () => {
    mockGet.mockRejectedValue(new Error('network'))
    const { result } = renderHook(() => useLLMConfig(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useLLMTest mutation', () => {
  it('calls test endpoint and returns result', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'connected', model: 'deepseek-chat', input_tokens: 0, output_tokens: 0, latency_ms: 10, finish_reason: 'stop' },
    })
    const { result } = renderHook(() => useLLMTest(), { wrapper })
    result.current.mutate({ prompt: 'ping' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.content).toBe('connected')
  })

  it('exposes pending state', async () => {
    mockPost.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useLLMTest(), { wrapper })
    result.current.mutate({ prompt: 'ping' })
    await waitFor(() => expect(result.current.isPending).toBe(true))
  })

  it('exposes error state', async () => {
    mockPost.mockRejectedValue(new Error('bad key'))
    const { result } = renderHook(() => useLLMTest(), { wrapper })
    result.current.mutate({ prompt: 'ping' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('LLM API shape and defaults', () => {
  it('fetchLLMConfig returns provider as string', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(typeof res.provider).toBe('string')
  })

  it('fetchLLMConfig returns api_key_set boolean', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(typeof res.api_key_set).toBe('boolean')
  })

  it('fetchLLMConfig supported providers includes deepseek', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.supported_providers).toContain('deepseek')
  })

  it('fetchLLMConfig supported providers includes openai', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.supported_providers).toContain('openai')
  })

  it('fetchLLMConfig supported providers includes mock', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const res = await fetchLLMConfig()
    expect(res.supported_providers).toContain('mock')
  })

  it('testLLM posts empty object when no request fields are set', async () => {
    mockPost.mockResolvedValue({ data: { success: true, content: '', model: '' } })
    await testLLM({})
    expect(mockPost).toHaveBeenCalledWith('/llm/test', {})
  })

  it('testLLM returns finish_reason', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'x', model: 'deepseek-chat', input_tokens: 1, output_tokens: 1, latency_ms: 1, finish_reason: 'length' },
    })
    const res = await testLLM({ prompt: 'x' })
    expect(res.finish_reason).toBe('length')
  })

  it('testLLM returns zero token counts when provider reports none', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, content: 'x', model: 'deepseek-chat', input_tokens: 0, output_tokens: 0, latency_ms: 1, finish_reason: 'stop' },
    })
    const res = await testLLM({ prompt: 'x' })
    expect(res.input_tokens).toBe(0)
    expect(res.output_tokens).toBe(0)
  })

  it('fetchLLMConfig rejects on network failure', async () => {
    mockGet.mockRejectedValue(new Error('network'))
    await expect(fetchLLMConfig()).rejects.toThrow('network')
  })

  it('testLLM rejects on network failure', async () => {
    mockPost.mockRejectedValue(new Error('network'))
    await expect(testLLM({ prompt: 'x' })).rejects.toThrow('network')
  })

  it('fetchLLMConfig forwards response data unchanged', async () => {
    mockGet.mockResolvedValue({ data: { ...configResponse, model: 'deepseek-reasoner' } })
    const res = await fetchLLMConfig()
    expect(res.model).toBe('deepseek-reasoner')
  })

  it('testLLM forwards prompt string unchanged', async () => {
    mockPost.mockResolvedValue({ data: { success: true, content: '', model: '' } })
    await testLLM({ prompt: 'ping' })
    expect(mockPost).toHaveBeenCalledWith('/llm/test', { prompt: 'ping' })
  })

  it('useLLMConfig data is undefined initially', async () => {
    mockGet.mockResolvedValue({ data: configResponse })
    const { result } = renderHook(() => useLLMConfig(), { wrapper })
    expect(result.current.data).toBeUndefined()
  })

  it('useLLMTest data is undefined initially', async () => {
    mockPost.mockResolvedValue({ data: { success: true, content: '', model: '' } })
    const { result } = renderHook(() => useLLMTest(), { wrapper })
    expect(result.current.data).toBeUndefined()
  })
})
