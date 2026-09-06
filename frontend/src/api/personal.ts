import apiClient from './client'

export interface EfficiencyInfo {
  average_duration_ms: number
  success_rate: number
  total_iterations: number
}

export interface KnowledgeGrowthInfo {
  knowledge_items_added: number
  experience_records_created: number
  artifacts_generated: number
}

export interface AgentActivityInfo {
  agents_active: number
  agents_total: number
  agent_executions_today: number
}

export interface PersonalMetrics {
  tasks_today: number
  tasks_completed_today: number
  tasks_failed_today: number
  tasks_running: number
  efficiency: EfficiencyInfo
  knowledge_growth: KnowledgeGrowthInfo
  agent_activity: AgentActivityInfo
  generated_at: string
}

export interface Insight {
  type: string
  title: string
  message: string
  priority: number
  action: string
}

export interface DailySummary {
  text: string
  lines: string[]
  mood: string
}

export interface PersonalDashboardResponse {
  success: boolean
  metrics: PersonalMetrics
  insights: Insight[]
  daily_summary: DailySummary
}

export const fetchPersonalDashboard = () =>
  apiClient.get<PersonalDashboardResponse>('/personal/dashboard').then((r) => r.data)
