import apiClient from "./client"

export interface MemoryItem {
  id: string
  user_id: string
  memory_type: string
  content: string
  importance: number
  embedding_id: string
  tags: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface SaveMemoryRequest {
  content: string
  memory_type?: string
  importance?: number
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface SearchMemoryRequest {
  query?: string
  memory_type?: string
  tags?: string[]
  limit?: number
  min_importance?: number
}

export interface MemoryListResponse {
  success: boolean
  total: number
  results: MemoryItem[]
}

export interface MemoryDetailResponse {
  success: boolean
  data?: MemoryItem
  error?: string
}

export interface MemoryStatsResponse {
  success: boolean
  data: {
    total_memories: number
    by_type: Record<string, number>
    total_tags: number
  }
}

export const saveMemory = (req: SaveMemoryRequest) =>
  apiClient.post<MemoryDetailResponse>("/memory/ltm", req).then((r) => r.data)

export const searchMemory = (req: SearchMemoryRequest) =>
  apiClient.post<MemoryListResponse>("/memory/ltm/search", req).then((r) => r.data)

export const getMemory = (id: string) =>
  apiClient.get<MemoryDetailResponse>("/memory/ltm/" + id).then((r) => r.data)

export const updateMemory = (id: string, req: Partial<SaveMemoryRequest>) =>
  apiClient.put<MemoryDetailResponse>("/memory/ltm/" + id, req).then((r) => r.data)

export const deleteMemory = (id: string) =>
  apiClient.delete<{ success: boolean }>("/memory/ltm/" + id).then((r) => r.data)

export const getMemoryStats = () =>
  apiClient.get<MemoryStatsResponse>("/memory/ltm/stats").then((r) => r.data)

export const getMemoryByType = (memoryType: string, limit = 50) =>
  apiClient
    .get<MemoryListResponse>("/memory/ltm/types/" + memoryType + "?limit=" + limit)
    .then((r) => r.data)

export const getProfile = () =>
  apiClient.get<MemoryListResponse>("/memory/ltm/profile").then((r) => r.data)

export const getPreferences = () =>
  apiClient.get<MemoryListResponse>("/memory/ltm/preferences").then((r) => r.data)

export const MEMORY_TYPES = ["profile", "preference", "project", "knowledge", "experience"] as const
export type MemoryTypeLabel = (typeof MEMORY_TYPES)[number]
