import apiClient from './client'

export interface ClusterInstance {
  instance_id: string
  status: string
  role: string
  started_at: string
}

export interface ClusterResponse {
  instances: ClusterInstance[]
  total: number
  leader: string | null
  self: string
  health: { persistence: string; redis: string }
  timestamp: string
}

export const fetchCluster = () =>
  apiClient.get<ClusterResponse>('/system/cluster').then((r) => r.data)