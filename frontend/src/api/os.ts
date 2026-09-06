import apiClient from './client'

export interface OSStatusResponse {
  success: boolean
  os_version: string
  components: Record<string, string>
  system_state: {
    agents_available: number; agents_active: number
    automations_running: number; tasks_queued: number; tasks_running: number
    last_improvement_at: string; overall_health: string
  }
  agents_available: number; agents_active: number
  tasks_running: number; tasks_queued: number
  overall_health: string
}

export interface OSInsight {
  type: string; message: string
}

export interface OSInsightsResponse {
  success: boolean
  context: Record<string, unknown>
  decision: { action: string; confidence: number; reasoning: string }
  suggestions: OSInsight[]
}

export interface OrchestrationStep {
  name: string; status: string; result: Record<string, unknown>
  error: string; duration_ms: number
}

export interface OSProcessResult {
  id: string; user_intent: string; success: boolean
  context: Record<string, unknown>
  decision: { action: string; confidence: number; reasoning: string; task_description: string
    recommended_agents: string[]; should_automate: boolean; should_learn: boolean; priority: number }
  steps: OrchestrationStep[]
  task_id: string; recommendations: string[]; generated_at: string
}

export interface OSProcessResponse {
  success: boolean
  result: OSProcessResult
}

export const fetchOSStatus = () =>
  apiClient.get<OSStatusResponse>('/os/status').then((r) => r.data)

export const fetchOSInsights = () =>
  apiClient.get<OSInsightsResponse>('/os/insights').then((r) => r.data)

export const processIntent = (intent: string, taskCategory = '') =>
  apiClient.post<OSProcessResponse>('/os/process', { intent, task_category: taskCategory }).then((r) => r.data)
