import apiClient from './client'
import type { AgentListResponse, RuntimeMetrics } from '../types'

// GET /api/v1/agents
export async function fetchAgents(): Promise<AgentListResponse> {
  const { data } = await apiClient.get('/agents')
  return data
}

// GET /api/v1/agents/:agentId
export async function fetchAgent(agentId: string) {
  const { data } = await apiClient.get(`/agents/${agentId}`)
  return data
}

// GET /api/v1/agents/status/runtime
export async function fetchRuntimeStatus() {
  const { data } = await apiClient.get('/agents/status/runtime')
  return data
}

// GET /api/v1/executions/metrics
export async function fetchMetrics(): Promise<RuntimeMetrics> {
  const { data } = await apiClient.get('/executions/metrics')
  return data
}

// GET /api/v1/executions/trace/all
export async function fetchAllTraces() {
  const { data } = await apiClient.get('/executions/trace/all')
  return data
}