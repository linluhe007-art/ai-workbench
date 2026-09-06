import apiClient from './client'

export interface LLMConfigInfo {
  provider: string
  model: string
  configured: boolean
  api_key_set: boolean
  supported_providers: string[]
}

export interface LLMTestRequest {
  prompt?: string
  model?: string | null
  temperature?: number
  max_tokens?: number
}

export interface LLMTestResponse {
  success: boolean
  content: string
  model: string
  input_tokens: number
  output_tokens: number
  latency_ms: number
  finish_reason: string
}

export const fetchLLMConfig = () =>
  apiClient.get<LLMConfigInfo>('/llm/config').then((r) => r.data)

export const testLLM = (req: LLMTestRequest) =>
  apiClient.post<LLMTestResponse>('/llm/test', req).then((r) => r.data)
