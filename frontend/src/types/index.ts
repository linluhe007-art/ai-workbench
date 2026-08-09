// API Response wrapper
export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

// Health check
export interface HealthStatus {
  status: string
  app?: string
  env?: string
  services?: Record<string, string>
}

// Agent
export interface Agent {
  id: string
  name: string
  type: string
  model: string
  capabilities: string[]
  status: 'online' | 'offline' | 'error'
}

// Task
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed'

export interface Task {
  id: string
  type: string
  status: TaskStatus
  agent_id: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown> | null
  created_at: string
}

// Content
export type ContentStatus = 'draft' | 'reviewing' | 'approved' | 'published'

export interface Content {
  id: string
  title: string
  body: string
  summary: string
  cover_url: string | null
  tags: string[]
  status: ContentStatus
  platform: string
  created_at: string
}

// User
export interface User {
  id: string
  username: string
  email: string
  nickname: string
  avatar_url: string | null
  role: string
}