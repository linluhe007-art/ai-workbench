import apiClient from "./client"

export interface TeamMember {
  id: string; role: string; agent_id: string; name: string
  capabilities: string[]; total_tasks: number; success_tasks: number
  success_rate: number; avg_duration_ms: number; active: boolean; created_at: string
}

export interface TeamStats {
  total_members: number; active_members: number
  total_tasks: number; total_success: number; overall_success_rate: number
}

export interface DelegationRecord {
  id: string; task_id: string; member_id: string; role: string
  success: boolean; duration_ms: number; created_at: string
}

export interface AgentRole {
  name: string; role: string; capabilities: string[]; tools: string[]; description: string
}

export const fetchPersonalAgents = () =>
  apiClient.get("/agents/personal").then((r) => r.data)

export const selectAgent = (taskType: string, capabilities?: string[], taskDescription?: string) =>
  apiClient.post("/agents/select", { task_type: taskType, capabilities: capabilities || [], task_description: taskDescription || "" }).then((r) => r.data)

export const fetchDelegations = (limit = 50) =>
  apiClient.get("/agents/personal/delegations?limit=" + limit).then((r) => r.data)

export const fetchAgentRoles = () =>
  apiClient.get("/agents/personal/roles").then((r) => r.data)
