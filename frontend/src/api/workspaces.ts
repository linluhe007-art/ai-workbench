import apiClient from './client'

export interface WorkspaceItemData {
  id: string
  name: string
  type: string
  content: unknown
  owner: string
  metadata: Record<string, unknown>
  created_at: string
}

// POST /api/v1/workspaces
export async function createWorkspace(taskId: string) {
  const { data } = await apiClient.post('/workspaces', { task_id: taskId })
  return data
}

// GET /api/v1/workspaces/{id}/items
export async function listWorkspaceItems(workspaceId: string) {
  const { data } = await apiClient.get(`/workspaces/${workspaceId}/items`)
  return data as { workspace_id: string; items: WorkspaceItemData[]; total: number }
}

// GET /api/v1/workspaces/{id}/items/{itemId}
export async function getWorkspaceItem(workspaceId: string, itemId: string) {
  const { data } = await apiClient.get(`/workspaces/${workspaceId}/items/${itemId}`)
  return data as WorkspaceItemData
}

// DELETE /api/v1/workspaces/{id}/items/{itemId}
export async function deleteWorkspaceItem(workspaceId: string, itemId: string) {
  const { data } = await apiClient.delete(`/workspaces/${workspaceId}/items/${itemId}`)
  return data
}