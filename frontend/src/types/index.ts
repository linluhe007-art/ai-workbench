// ── Backend API Types ──────────────────────────────────────

// Task (matches backend TaskRecord.to_dict())
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'queued' | 'paused' | 'cancelled' | 'timeout'

export interface TaskRecord {
  attempt?: number
  max_iterations?: number
  timeout_seconds?: number | null
  error_message?: string | null
  task_id: string
  task: string
  status: TaskStatus
  created_at: string
  updated_at: string
  iterations?: number
  success?: boolean
  evaluation?: {
    score: number
    quality: string
    issues: string[]
  }
  execution?: {
    status: string
    duration_ms: number
    success_count: number
    failed_count: number
  }
}

export interface TaskCreateRequest {
  task: string
  max_iterations?: number
}

export interface TaskCreateResponse {
  task_id: string
  task: string
  status: string
}

// Agent (matches backend AgentRuntime.list_agents())
export interface AgentInfo {
  id: string
  name: string
  type: string
  state: string
  capabilities: string[]
  config?: Record<string, unknown>
}

export interface AgentListResponse {
  agents: AgentInfo[]
  total: number
}

// Runtime Metrics (matches backend RuntimeMetrics.compute())
export interface RuntimeMetrics {
  total_tasks: number
  success_rate: number
  average_duration_ms: number
  agent_runs: number
  agent_success_rate: number
  total_steps: number
  step_failure_rate: number
  total_errors: number
}

// Trace Event (matches backend TraceEvent.to_dict())
export interface TraceEvent {
  trace_id: string
  task_id: string
  component: string
  event_type: string
  timestamp: string
  duration_ms: number
  metadata: Record<string, unknown>
}

export interface TraceResponse {
  events: TraceEvent[]
  total: number
}

// WebSocket Events
export interface WsEvent {
  event: string
  task_id: string
  timestamp: string
  data: Record<string, unknown>
}

// Health
export interface HealthStatus {
  status: string
  app?: string
  env?: string
  services?: Record<string, string>
}

// User (existing)
export interface User {
  id: string
  username: string
  email: string
  nickname: string
  avatar_url: string | null
  role: string
}