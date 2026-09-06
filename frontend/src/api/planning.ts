import apiClient from './client'

export interface PlanningDebugSession {
  session_id: string
  task: string
  planner_type: string
  prompt: string | null
  raw_response: string | null
  parsed_plan: {
    intent: string
    steps: Array<{
      id: string
      type: string
      description: string
      depends_on: string[]
      agent_hint: string
    }>
  } | null
  selected_agents: Record<string, string>
  capabilities: Record<string, string[]>
  fallback_used: boolean
  error: string | null
  duration_ms: number
  created_at: string
}

// POST /api/v1/planning/debug
export async function debugPlanning(task: string): Promise<PlanningDebugSession> {
  const { data } = await apiClient.post('/planning/debug', { task })
  return data
}

// GET /api/v1/planning/debug/{sessionId}
export async function fetchPlanningSession(sessionId: string): Promise<PlanningDebugSession> {
  const { data } = await apiClient.get(`/planning/debug/${sessionId}`)
  return data
}

// GET /api/v1/planning/debug
export async function fetchPlanningSessions() {
  const { data } = await apiClient.get('/planning/debug')
  return data as { sessions: PlanningDebugSession[]; total: number }
}