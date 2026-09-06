import apiClient from './client'

export interface WorkflowStep {
  id: string
  type: string
  description: string
  agent: string
  depends_on: string[]
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  started_at: string | null
  finished_at: string | null
  duration: number
  error?: string | null
}

export interface WorkflowData {
  task_id: string
  intent: string
  steps: WorkflowStep[]
  total_steps: number
}

// GET /api/v1/tasks/{taskId}/workflow
export async function fetchWorkflow(taskId: string): Promise<WorkflowData> {
  const { data } = await apiClient.get(`/tasks/${taskId}/workflow`)
  return data
}