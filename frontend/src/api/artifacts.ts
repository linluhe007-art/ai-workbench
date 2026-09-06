import apiClient from "./client"

export interface ArtifactItem {
  id: string
  name: string
  type: string
  content: string
  owner: string
  metadata: Record<string, unknown>
  created_at: string
  workspace_id?: string
}

export interface TaskArtifactsResponse {
  task_id: string
  artifacts: ArtifactItem[]
  total: number
}

export async function fetchTaskArtifacts(taskId: string): Promise<TaskArtifactsResponse> {
  const { data } = await apiClient.get(`/tasks/${taskId}/artifacts`)
  return data
}

export async function fetchArtifact(artifactId: string): Promise<ArtifactItem> {
  const { data } = await apiClient.get(`/artifacts/${artifactId}`)
  return data
}

export async function deleteArtifact(artifactId: string): Promise<{ deleted: boolean; artifact_id: string; workspace_id: string }> {
  const { data } = await apiClient.delete(`/artifacts/${artifactId}`)
  return data
}

export async function renameArtifact(artifactId: string, name: string): Promise<ArtifactItem> {
  const { data } = await apiClient.post(`/artifacts/${artifactId}/rename`, { name })
  return data
}