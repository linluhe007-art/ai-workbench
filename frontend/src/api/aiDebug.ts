import apiClient from './client'

export interface DecisionTrace {
  id: string; user_id: string; task_id: string; trace_type: string
  component: string; input_data: Record<string, unknown>; decision: Record<string, unknown>
  reason: string; confidence: number; metadata: Record<string, unknown>; created_at: string
}

export interface TracesResponse { success: boolean; traces: DecisionTrace[]; total: number }

export interface PromptInfo {
  id: string; name: string; version: number; content: string
  variables: string[]; description: string; active: boolean; created_at: string
}

export interface PromptsResponse { success: boolean; prompts: PromptInfo[]; total: number }

export interface AIUsageRecord {
  id: string; model: string; provider: string; tokens_input: number; tokens_output: number
  latency_ms: number; cost: number; task_id: string; agent_id: string; created_at: string
}

export interface AIUsageResponse { success: boolean; records: AIUsageRecord[] }

export interface AISummary { total_records: number; total_tokens: number; total_cost: number; average_latency_ms: number; model_usage: Record<string, number> }

export interface AISummaryResponse { success: boolean; summary: AISummary }

export interface ContextData { id: string; task_id: string; user_input: string; memory_context: Record<string,unknown>; knowledge_context: Record<string,unknown>; plan: Record<string,unknown>; agent: string; prompt: string; model: string; result: Record<string,unknown> }

export const fetchTraces = (params: Record<string, string> = {}) => {
  const qs = new URLSearchParams(params).toString()
  return apiClient.get<TracesResponse>(`/intelligence/traces?${qs}`).then(r => r.data)
}
export const fetchTaskTrace = (taskId: string) => apiClient.get<TracesResponse>(`/intelligence/tasks/${taskId}/decision-trace`).then(r => r.data)
export const fetchPrompts = () => apiClient.get<PromptsResponse>('/prompts').then(r => r.data)
export const fetchAIUsage = () => apiClient.get<AIUsageResponse>('/analytics/ai-usage').then(r => r.data)
export const fetchAISummary = () => apiClient.get<AISummaryResponse>('/analytics/ai-summary').then(r => r.data)
