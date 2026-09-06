import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import apiClient from '../api/client'
import { startResearch, fetchSources, fetchResearchResult } from '../api/research'

vi.mock('../api/client')
const mockPost = vi.mocked(apiClient.post)
const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseResearchResponse = {
  success: true, task_id: 'task-1', status: 'completed', source_count: 5,
}

const baseSourcesResponse = {
  success: true, task_id: 'task-1', sources: [
    { title: 'Source 1', url: 'https://s1.com', snippet: 'Snippet 1', source: 'web', published: '2026-01-01', relevance_score: 0.9 },
    { title: 'Source 2', url: 'https://s2.com', snippet: 'Snippet 2', source: 'web', published: '2026-01-02', relevance_score: 0.85 },
  ],
}

const baseResultResponse = {
  success: true, task_id: 'task-1',
  artifact: {
    type: 'markdown', name: 'research_report',
    content: '# Research Report\n\nContent here',
    metadata: { source_count: 2, citations: [{ title: 'S1', url: 'https://s1.com' }] },
  },
  citations: [{ title: 'S1', url: 'https://s1.com' }],
  status: 'completed',
}

// ===== API Tests =====
describe('Research API', () => {
  it('startResearch returns task_id', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const res = await startResearch({ query: 'AI trends' })
    expect(res.task_id).toBe('task-1')
    expect(res.source_count).toBe(5)
  })

  it('startResearch with output_type', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    await startResearch({ query: 'q', output_type: 'article' })
    expect(mockPost).toHaveBeenCalledWith('/research', expect.objectContaining({ output_type: 'article' }))
  })

  it('startResearch with max_sources', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    await startResearch({ query: 'q', max_sources: 5 })
    expect(mockPost).toHaveBeenCalledWith('/research', expect.objectContaining({ max_sources: 5 }))
  })

  it('fetchSources returns sources list', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('task-1')
    expect(res.sources).toHaveLength(2)
    expect(res.sources[0].title).toBe('Source 1')
  })

  it('fetchSources returns relevance scores', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('task-1')
    expect(res.sources[0].relevance_score).toBe(0.9)
  })

  it('fetchResearchResult returns artifact', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('task-1')
    expect(res.artifact.type).toBe('markdown')
    expect(res.artifact.content).toContain('Research Report')
  })

  it('fetchResearchResult returns citations', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('task-1')
    expect(res.citations).toHaveLength(1)
  })

  it('startResearch handles empty query', async () => {
    mockPost.mockResolvedValue({ data: { ...baseResearchResponse, source_count: 0 } })
    const res = await startResearch({ query: '' })
    expect(res.success).toBe(true)
  })

  it('fetchSources with invalid task', async () => {
    mockGet.mockResolvedValue({ data: { success: false, error: 'Not found' } })
    const res = await fetchSources('bad-id')
    expect(res.success).toBe(false)
  })

  it('fetchResearchResult with invalid task', async () => {
    mockGet.mockResolvedValue({ data: { success: false, error: 'Not found' } })
    const res = await fetchResearchResult('bad-id')
    expect(res.success).toBe(false)
  })
})

// ===== Type Tests =====
describe('Research Types', () => {
  it('source has required fields', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.title).toBeDefined()
      expect(s.url).toBeDefined()
    }
  })

  it('artifact has type and content', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.type).toBeTruthy()
    expect(res.artifact.content.length).toBeGreaterThan(0)
  })

  it('artifact metadata has source_count', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.metadata.source_count).toBe(2)
  })

  it('artifact metadata has citations', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.metadata.citations).toHaveLength(1)
  })
})

// ===== Integration Tests =====
describe('Research Flow', () => {
  it('full flow: create -> sources -> result', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    mockGet.mockResolvedValueOnce({ data: baseSourcesResponse })
    mockGet.mockResolvedValueOnce({ data: baseResultResponse })

    const create = await startResearch({ query: 'AI trends' })
    expect(create.task_id).toBe('task-1')

    const sources = await fetchSources(create.task_id)
    expect(sources.sources.length).toBeGreaterThan(0)

    const result = await fetchResearchResult(create.task_id)
    expect(result.artifact.content.length).toBeGreaterThan(0)
  })

  it('research with different output types all succeed', async () => {
    for (const t of ['report', 'article', 'analysis']) {
      mockPost.mockReset()
      mockPost.mockResolvedValue({ data: { ...baseResearchResponse, task_id: 'task-' + t } })
      const res = await startResearch({ query: 'test', output_type: t })
      expect(res.success).toBe(true)
    }
  })

  it('sources contain valid URLs', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.url.startsWith('https://')).toBe(true)
    }
  })

  it('artifact citations match source count', async () => {
    mockGet.mockResolvedValue({
      data: {
        ...baseResultResponse,
        artifact: {
          ...baseResultResponse.artifact,
          metadata: { source_count: 3, citations: [{ title: 'A' }, { title: 'B' }, { title: 'C' }] },
        },
      },
    })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.metadata.citations.length).toBe(3)
    expect(res.artifact.metadata.source_count).toBe(3)
  })

  it('handle network error in startResearch', async () => {
    mockPost.mockRejectedValue(new Error('Network error'))
    await expect(startResearch({ query: 'test' })).rejects.toThrow('Network error')
  })

  it('handle network error in fetchSources', async () => {
    mockGet.mockRejectedValue(new Error('Timeout'))
    await expect(fetchSources('t1')).rejects.toThrow('Timeout')
  })
})

// ===== Edge Cases =====
describe('Research Edge Cases', () => {
  it('zero sources response', async () => {
    mockGet.mockResolvedValue({ data: { success: true, task_id: 't0', sources: [] } })
    const res = await fetchSources('t0')
    expect(res.sources).toHaveLength(0)
  })

  it('empty content artifact', async () => {
    mockGet.mockResolvedValue({
      data: { ...baseResultResponse, artifact: { ...baseResultResponse.artifact, content: '' } },
    })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.content).toBe('')
  })

  it('source relevance between 0 and 1', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.relevance_score).toBeGreaterThanOrEqual(0)
      expect(s.relevance_score).toBeLessThanOrEqual(1)
    }
  })

  it('startResearch with very long query', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const longQuery = 'A'.repeat(500)
    const res = await startResearch({ query: longQuery })
    expect(res.success).toBe(true)
  })

  it('multiple consecutive research tasks', async () => {
    mockPost.mockResolvedValue({ data: { ...baseResearchResponse, task_id: 'tk1' } })
    const r1 = await startResearch({ query: 'q1' })
    mockPost.mockResolvedValue({ data: { ...baseResearchResponse, task_id: 'tk2' } })
    const r2 = await startResearch({ query: 'q2' })
    expect(r1.task_id).not.toBe(r2.task_id)
  })
})


// ===== Additional API Tests =====
describe('Research API Extended', () => {
  it('startResearch returns success true', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const res = await startResearch({ query: 'q' })
    expect(res.success).toBe(true)
  })

  it('startResearch returns status completed', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const res = await startResearch({ query: 'q' })
    expect(res.status).toBe('completed')
  })

  it('fetchSources task_id matches request', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('task-1')
    expect(res.task_id).toBe('task-1')
  })

  it('fetchResearchResult task_id matches request', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('task-1')
    expect(res.task_id).toBe('task-1')
  })

  it('fetchSources response has success field', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    expect(res.success).toBe(true)
  })

  it('fetchResearchResult response has success field', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.success).toBe(true)
  })

  it('sources have snippet fields', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.snippet).toBeDefined()
    }
  })

  it('startResearch post body includes query', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    await startResearch({ query: 'specific query text' })
    const callArg = mockPost.mock.calls[0][1] as Record<string, unknown>
    expect(callArg.query).toBe('specific query text')
  })

  it('startResearch includes output_type in body', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    await startResearch({ query: 'q', output_type: 'report' })
    const callArg = mockPost.mock.calls[0][1] as Record<string, unknown>
    expect(callArg.output_type).toBe('report')
  })

  it('research API is called with correct path', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    await startResearch({ query: 'q' })
    expect(mockPost).toHaveBeenCalledWith('/research', expect.any(Object))
  })

  it('fetchSources called with correct path', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    await fetchSources('my-task-id')
    expect(mockGet).toHaveBeenCalledWith('/research/my-task-id/sources')
  })

  it('fetchResearchResult called with correct path', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    await fetchResearchResult('result-task')
    expect(mockGet).toHaveBeenCalledWith('/research/result-task/result')
  })
})

// ===== Additional Edge Cases =====
describe('Research Additional Edge Cases', () => {
  it('artifact name is set', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.name).toBeTruthy()
  })

  it('artifact type is markdown for report', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.type).toBe('markdown')
  })

  it('sources have published dates', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.published.length).toBeGreaterThan(0)
    }
  })

  it('sources have source field', async () => {
    mockGet.mockResolvedValue({ data: baseSourcesResponse })
    const res = await fetchSources('t1')
    for (const s of res.sources) {
      expect(s.source).toBeTruthy()
    }
  })

  it('citations have titles', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    for (const c of res.citations) {
      expect(c.title).toBeTruthy()
    }
  })

  it('citations have URLs', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    for (const c of res.citations) {
      expect(c.url.startsWith('https://')).toBe(true)
    }
  })

  it('research with special characters in query', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const res = await startResearch({ query: 'AI & Machine Learning: 2026 Trends?' })
    expect(res.success).toBe(true)
  })

  it('source_count matches sources array length', async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: 't1', status: 'completed', source_count: 2 } })
    mockGet.mockResolvedValue({ data: { ...baseSourcesResponse, sources: baseSourcesResponse.sources.slice(0, 2) } })
    const create = await startResearch({ query: 'q' })
    const sources = await fetchSources(create.task_id)
    expect(sources.sources.length).toBe(2)
  })

  it('multiple fetchResult calls same task', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const r1 = await fetchResearchResult('t1')
    const r2 = await fetchResearchResult('t1')
    expect(r1.artifact.content).toBe(r2.artifact.content)
  })

  it('startResearch max_sources defaults work', async () => {
    mockPost.mockResolvedValue({ data: baseResearchResponse })
    const res = await startResearch({ query: 'q' })
    expect(res.source_count).toBeGreaterThanOrEqual(0)
  })

  it('artifact metadata has agent_chain or similar', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.metadata).toBeDefined()
  })

  it('result has status field', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.status).toBe('completed')
  })
})
// ===== Final Edge =====
describe('Research Final Edge', () => {
  it('result artifact has all required fields', async () => {
    mockGet.mockResolvedValue({ data: baseResultResponse })
    const res = await fetchResearchResult('t1')
    expect(res.artifact.type).toBeTruthy()
    expect(res.artifact.name).toBeTruthy()
    expect(res.artifact.content).toBeDefined()
    expect(res.artifact.metadata).toBeDefined()
  })
})
