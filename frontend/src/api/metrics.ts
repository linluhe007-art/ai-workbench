import apiClient from './client'

export interface MetricsResponse {
  cpu: { percent: number }
  memory: { total_gb: number; available_gb: number; percent: number; process_mb: number }
  runtime: { instance_id: string; uptime_seconds: number; status: string; persistence_enabled: boolean; redis_enabled: boolean }
  tasks: { total: number; created: number; completed: number; failed: number; timeout: number; cancelled: number }
  queue: { running: number; queued: number; max_concurrent: number }
  agents: { total_executions: number; success_rate: number; latency: { avg: number; p50: number; p95: number } }
}

export interface TaskMetricsResponse {
  total: number; completed: number; failed: number; timeout: number; cancelled: number
  success_rate: number; failure_rate: number; average_duration_ms: number
}

export interface AgentMetricsResponse {
  total_executions: number
  agents: Array<{ agent_id: string; executions: number; errors: number; latency: { avg: number } }>
}

export const fetchMetrics = () =>
  apiClient.get<MetricsResponse>('/metrics').then((r) => r.data)

export const fetchTaskMetrics = () =>
  apiClient.get<TaskMetricsResponse>('/metrics/tasks').then((r) => r.data)

export const fetchAgentMetrics = () =>
  apiClient.get<AgentMetricsResponse>('/metrics/agents').then((r) => r.data)
