import apiClient from './client'

export interface TaskAnalysis {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  success_rate: number
  average_duration_ms: number
}

export interface AgentPerformance {
  agent_id: string
  executions: number
  errors: number
  success_rate: number
}

export interface Bottleneck {
  type: string
  severity: string
  detail: string
  suggestion: string
}

export interface AnalysisData {
  generated_at: string
  task_analysis: TaskAnalysis
  agent_performance: AgentPerformance[]
  best_agent: string
  worst_agent: string
  workflow_stats: Record<string, unknown>
  bottlenecks: Bottleneck[]
}

export interface StrategyRecommendation {
  id: string
  category: string
  title: string
  description: string
  priority: number
  expected_impact: string
  action: Record<string, unknown>
}

export interface StrategyPlan {
  generated_at: string
  recommendations: StrategyRecommendation[]
  summary: string
}

export interface ImprovementReportResponse {
  success: boolean
  analysis: AnalysisData
  strategy_plan: StrategyPlan
}

export interface OptimizationRecord {
  id: string
  recommendation_id: string
  category: string
  title: string
  action: Record<string, unknown>
  status: string
  applied_at: string
  result: Record<string, unknown>
}

export interface ApplyResponse {
  success: boolean
  applied: number
  records: OptimizationRecord[]
}

export interface HistoryResponse {
  success: boolean
  records: OptimizationRecord[]
  stats: { total_applied: number; by_category: Record<string, number> }
}

export const fetchImprovementReport = () =>
  apiClient.get<ImprovementReportResponse>('/improvement/report').then((r) => r.data)

export const applyImprovement = (recommendationIds: string[] = []) =>
  apiClient.post<ApplyResponse>('/improvement/apply', { recommendation_ids: recommendationIds }).then((r) => r.data)

export const fetchImprovementHistory = () =>
  apiClient.get<HistoryResponse>('/improvement/history').then((r) => r.data)

export const revertImprovement = (recordId: string) =>
  apiClient.post(`/improvement/revert/${recordId}`).then((r) => r.data)
