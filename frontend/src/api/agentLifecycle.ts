import apiClient from './client'

export interface AgentRegistryItem {
  agent_id: string
  name: string
  capabilities: string[]
  enabled: boolean
  alive: boolean
  last_heartbeat: string | null
  lifecycle_state: string
  active_tasks: number
  max_concurrent: number
}

export interface AgentRegistryResponse {
  agents: AgentRegistryItem[]
  total: number
}

export interface AgentRuntimeResponse {
  agent_id: string
  name: string
  state: string
  task: string
  started_at: string | null
  completed_at: string | null
  error: string
  load: { active_tasks: number; max_concurrent: number }
  capabilities: string[]
}

export const fetchAgentRegistry = () =>
  apiClient.get<AgentRegistryResponse>('/agents/registry').then((r) => r.data)

export const registerAgent = (agentId: string, capabilities: string[]) =>
  apiClient.post('/agents/register', { agent_id: agentId, capabilities }).then((r) => r.data)

export const sendHeartbeat = (agentId: string) =>
  apiClient.post(`/agents/${agentId}/heartbeat`).then((r) => r.data)

export const disableAgent = (agentId: string) =>
  apiClient.post(`/agents/${agentId}/disable`).then((r) => r.data)

export const enableAgent = (agentId: string) =>
  apiClient.post(`/agents/${agentId}/enable`).then((r) => r.data)

export const fetchAgentRuntime = (agentId: string) =>
  apiClient.get<AgentRuntimeResponse>(`/agents/${agentId}/runtime`).then((r) => r.data)