import { useQuery } from '@tanstack/react-query'
import { fetchTraces, fetchTaskTrace, fetchPrompts, fetchAIUsage, fetchAISummary } from '../api/aiDebug'

export function useTraces(params: Record<string, string> = {}) {
  return useQuery({ queryKey: ['traces', params], queryFn: () => fetchTraces(params), refetchInterval: 10000 })
}
export function useTaskTrace(taskId: string | null) {
  return useQuery({ queryKey: ['task-trace', taskId], queryFn: () => fetchTaskTrace(taskId!), enabled: !!taskId })
}
export function useDebugPrompts() {
  return useQuery({ queryKey: ['debug-prompts'], queryFn: fetchPrompts, refetchInterval: 30000 })
}
export function useAIUsage() {
  return useQuery({ queryKey: ['ai-usage'], queryFn: fetchAIUsage, refetchInterval: 15000 })
}
export function useAISummary() {
  return useQuery({ queryKey: ['ai-summary'], queryFn: fetchAISummary, refetchInterval: 15000 })
}
