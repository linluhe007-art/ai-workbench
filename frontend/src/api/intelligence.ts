import apiClient from './client'

export interface IntentResponse {
  task_type: string
  complexity: string
  required_agents: string[]
  required_tools: string[]
  confidence: number
  metadata: Record<string, unknown>
}

export interface CommandResponse {
  success: boolean
  intent: IntentResponse
  task_id: string
  classification: { task_type: string; confidence: number; keywords_matched: string[] }
  confidence: number
  created_at: string
}

export interface HistoryResponse {
  history: Array<{ prompt: string; intent: IntentResponse; task_id: string; created_at: string }>
  total: number
}

export const processCommand = (prompt: string) =>
  apiClient.post<CommandResponse>('/intelligence/command', { prompt }).then((r) => r.data)

export const fetchCommandHistory = () =>
  apiClient.get<HistoryResponse>('/intelligence/history').then((r) => r.data)