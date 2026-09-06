import apiClient from './client'

export interface ExperienceResult {
  task_pattern: string
  agents: string[]
  success: boolean
  duration_ms: number
  match_score?: number
  score?: number
  metadata: Record<string, unknown>
  created_at: string
}

export interface ExperienceSearchResponse {
  query: string
  results: ExperienceResult[]
  total: number
}

export interface ExperienceStats {
  experience: {
    total_records: number
    success_count: number
    failure_count: number
    success_rate: number
    top_patterns: Array<{ pattern: string; count: number; success_rate: number }>
    top_agents: Array<{ agent_id: string; success_rate: number; total: number }>
    recent_failures: Array<{ task_pattern: string; agents: string[]; error: string; created_at: string }>
  }
  feedback: {
    total: number
    average_rating: number
    ratings: Array<{ task_id: string; pattern: string; rating: number }>
  }
}

export interface ExperienceRecommendations {
  task_pattern: string
  recommended_agents: string[]
  historical_success_rate: number
  similar_experiences_count: number
  warnings: string[]
}

export const searchExperience = (q: string, success?: boolean, limit = 20) =>
  apiClient.get<ExperienceSearchResponse>('/experience/search', { params: { q, success, limit } }).then((r) => r.data)

export const submitFeedback = (taskId: string, rating: number, comment = '', taskPattern = '') =>
  apiClient.post('/experience/feedback', { task_id: taskId, task_pattern: taskPattern, rating, comment }).then((r) => r.data)

export const fetchExperienceStats = () =>
  apiClient.get<ExperienceStats>('/experience/stats').then((r) => r.data)

export const fetchRecommendations = (taskPattern: string) =>
  apiClient.get<ExperienceRecommendations>('/experience/recommendations', { params: { task_pattern: taskPattern } }).then((r) => r.data)