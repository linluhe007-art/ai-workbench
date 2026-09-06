import apiClient from './client'

export interface SystemHealth {
  status: string
  timestamp?: string
  service?: string
}

export interface SystemReadiness {
  ready: boolean
  status: string
  persistence?: string
  redis?: string
  instance_id?: string
  uptime_seconds?: number
  timestamp?: string
}

export interface SystemInfo {
  instance_id?: string
  started_at?: string
  status?: string
  active_tasks?: number
  queued_tasks?: number
  total_tasks?: number
  health?: {
    status: string
    persistence_status: string
    redis_status: string
    uptime_seconds: number
    components: Record<string, string>
    max_concurrent?: number
  }
  metrics?: {
    total_tasks: number
    success_rate: number
    average_duration: number
  }
}

export const fetchSystemHealth = () =>
  apiClient.get<SystemHealth>('/system/health').then((r) => r.data)

export const fetchSystemInfo = () =>
  apiClient.get<SystemInfo>('/system/info').then((r) => r.data)

export const fetchReadiness = () =>
  apiClient.get<SystemReadiness>('/system/readiness').then((r) => r.data)

export const fetchSystemMetrics = () =>
  apiClient.get('/system/metrics').then((r) => r.data)
