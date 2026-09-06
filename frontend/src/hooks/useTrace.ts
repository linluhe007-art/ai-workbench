import { useQuery } from '@tanstack/react-query'
import { fetchTaskTrace, fetchTaskHistory } from '../api/tasks'

export function useTaskTrace(taskId: string | null) {
  return useQuery({
    queryKey: ['task-trace', taskId],
    queryFn: () => fetchTaskTrace(taskId!),
    enabled: !!taskId,
    refetchInterval: 5000,
  })
}

export function useTaskHistory(taskId: string | null) {
  return useQuery({
    queryKey: ['task-history', taskId],
    queryFn: () => fetchTaskHistory(taskId!),
    enabled: !!taskId,
    refetchInterval: 5000,
  })
}