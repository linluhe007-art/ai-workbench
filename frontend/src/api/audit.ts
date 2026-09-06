import apiClient from './client'

export interface AuditQueryParams {
  task_id?: string | null
  actor?: string | null
  action?: string | null
  resource_type?: string | null
  resource_id?: string | null
  request_id?: string | null
  limit?: number
  offset?: number
}

export interface AuditRecord {
  id: string
  timestamp: string
  actor: string
  action: string
  resource_type: string
  resource_id: string
  task_id: string | null
  request_id: string | null
  before: Record<string, unknown>
  after: Record<string, unknown>
  metadata: Record<string, unknown>
}

export interface AuditQueryResponse {
  items: AuditRecord[]
  total: number
  limit: number
  offset: number
}

export interface TaskAuditTrailResponse {
  task_id: string
  audit_trail: AuditRecord[]
  total: number
  exists: boolean
}

export interface AgentAuditResponse {
  agent_id: string
  items: AuditRecord[]
  total: number
}

export interface AuditStatsResponse {
  total_records: number
  status: string
}

export async function fetchAuditRecords(params: AuditQueryParams = {}): Promise<AuditQueryResponse> {
  const cleanParams: Record<string, string | number> = {}
  if (params.task_id) cleanParams.task_id = params.task_id
  if (params.actor) cleanParams.actor = params.actor
  if (params.action) cleanParams.action = params.action
  if (params.resource_type) cleanParams.resource_type = params.resource_type
  if (params.resource_id) cleanParams.resource_id = params.resource_id
  if (params.request_id) cleanParams.request_id = params.request_id
  if (params.limit !== undefined) cleanParams.limit = params.limit
  if (params.offset !== undefined) cleanParams.offset = params.offset

  const { data } = await apiClient.get('/audit', { params: cleanParams })
  return data
}

export async function fetchTaskAuditTrail(taskId: string): Promise<TaskAuditTrailResponse> {
  const { data } = await apiClient.get(`/tasks/${taskId}/audit`)
  return data
}

export async function fetchAgentAudit(agentId: string, limit = 100): Promise<AgentAuditResponse> {
  const { data } = await apiClient.get(`/agents/${agentId}/audit`, { params: { limit } })
  return data
}

export async function fetchAuditStats(): Promise<AuditStatsResponse> {
  const { data } = await apiClient.get('/audit/stats')
  return data
}