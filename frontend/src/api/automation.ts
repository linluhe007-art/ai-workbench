import apiClient from './client'

export interface AutomationTrigger {
  trigger_type: string
  cron_expression: string
  event_name: string
  webhook_url: string
  metadata: Record<string, unknown>
}

export interface Automation {
  id: string
  name: string
  description: string
  trigger: AutomationTrigger
  action: Record<string, unknown>
  status: string
  last_run_at: string
  run_count: number
  created_at: string
  updated_at: string
}

export interface AutomationListResponse {
  success: boolean
  automations: Automation[]
  total: number
}

export interface CreateAutomationRequest {
  name: string
  description?: string
  trigger_type?: string
  cron_expression?: string
  event_name?: string
  action_type?: string
  action_params?: Record<string, unknown>
  max_iterations?: number
}

export interface CreateAutomationResponse {
  success: boolean
  automation: Automation
}

export interface ExecutionLog {
  id: string
  automation_id: string
  status: string
  result: Record<string, unknown>
  error: string
  started_at: string
  finished_at: string
  created_at: string
}

export interface ExecutionLogsResponse {
  success: boolean
  logs: ExecutionLog[]
  total: number
}

export interface RunAutomationResponse {
  success: boolean
  log: ExecutionLog | null
}

export const fetchAutomations = () =>
  apiClient.get<AutomationListResponse>('/automation').then((r) => r.data)

export const createAutomation = (req: CreateAutomationRequest) =>
  apiClient.post<CreateAutomationResponse>('/automation', req).then((r) => r.data)

export const fetchAutomation = (id: string) =>
  apiClient.get<{ success: boolean; automation: Automation }>(`/automation/${id}`).then((r) => r.data)

export const runAutomation = (id: string) =>
  apiClient.post<RunAutomationResponse>(`/automation/${id}/run`).then((r) => r.data)

export const updateAutomationStatus = (id: string, status: string) =>
  apiClient.put<{ success: boolean }>(`/automation/${id}/status?status=${status}`).then((r) => r.data)

export const deleteAutomation = (id: string) =>
  apiClient.delete<{ success: boolean }>(`/automation/${id}`).then((r) => r.data)

export const fetchAutomationLogs = (id: string, limit = 50) =>
  apiClient.get<ExecutionLogsResponse>(`/automation/${id}/logs?limit=${limit}`).then((r) => r.data)
