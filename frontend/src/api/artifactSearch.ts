import apiClient from "./client"
import type { ArtifactItem } from "./artifacts"

export interface ArtifactSearchParams {
  q?: string
  type?: string
  agent_id?: string
  task_id?: string
  workspace_id?: string
  step_id?: string
  created_after?: string
  created_before?: string
  sort_by?: "created_at" | "name" | "type"
  order?: "asc" | "desc"
  limit?: number
  offset?: number
}

export interface ArtifactSearchResponse {
  items: ArtifactItem[]
  total: number
  limit: number
  offset: number
}

export async function searchArtifacts(params: ArtifactSearchParams): Promise<ArtifactSearchResponse> {
  const clean: Record<string, string | number> = {}
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      clean[k] = v
    }
  }
  const { data } = await apiClient.get("/artifacts/search", { params: clean })
  return data
}