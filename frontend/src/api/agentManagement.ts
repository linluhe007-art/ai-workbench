import apiClient from './client'

export interface AgentCapabilities {
  agent_id: string
  capabilities: string[]
  metadata: Record<string, unknown>
  experience: {
    task_count: number
    success_rate: number
  }
}

export interface AgentHealth {
  agent_id: string
  healthy: boolean
  state: string
  last_heartbeat: string | null
  error: string | null
}

export interface AgentHistoryRecord {
  task_id: string
  success: boolean
  duration: number
  created_at: string
}

export interface AgentHistory {
  agent_id: string
  records: AgentHistoryRecord[]
  total: number
}

export interface CapabilityAggregate {
  name: string
  agents: string[]
  count: number
}

// GET /api/v1/agents/{id}/capabilities
export async function fetchAgentCapabilities(agentId: string): Promise<AgentCapabilities> {
  const { data } = await apiClient.get(`/agents/${agentId}/capabilities`)
  return data
}

// GET /api/v1/agents/{id}/health
export async function fetchAgentHealth(agentId: string): Promise<AgentHealth> {
  const { data } = await apiClient.get(`/agents/${agentId}/health`)
  return data
}

// GET /api/v1/agents/{id}/history
export async function fetchAgentHistory(agentId: string): Promise<AgentHistory> {
  const { data } = await apiClient.get(`/agents/${agentId}/history`)
  return data
}

// GET /api/v1/agents/capabilities/all
export async function fetchAllCapabilities(): Promise<{ capabilities: CapabilityAggregate[]; total: number }> {
  const { data } = await apiClient.get('/agents/capabilities/all')
  return data
}