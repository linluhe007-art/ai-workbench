import apiClient from './client'

export interface ResearchRequest {
  query: string
  output_type?: string
  max_sources?: number
}

export interface ResearchResponse {
  success: boolean
  task_id: string
  status: string
  source_count: number
}

export interface SourcesResponse {
  success: boolean
  task_id: string
  sources: Array<{
    title: string
    url: string
    snippet: string
    source: string
    published: string
    relevance_score: number
  }>
}

export interface ResultResponse {
  success: boolean
  task_id: string
  artifact: {
    type: string
    name: string
    content: string
    metadata: Record<string, unknown>
  }
  citations: Array<{ title: string; url: string }>
  status: string
}

export const startResearch = (req: ResearchRequest): Promise<ResearchResponse> =>
  apiClient.post('/research', req).then(r => r.data)

export const fetchSources = (taskId: string): Promise<SourcesResponse> =>
  apiClient.get(`/research/${taskId}/sources`).then(r => r.data)

export const fetchResearchResult = (taskId: string): Promise<ResultResponse> =>
  apiClient.get(`/research/${taskId}/result`).then(r => r.data)
