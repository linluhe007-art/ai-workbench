import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { debugPlanning, fetchPlanningSession, fetchPlanningSessions } from '../api/planning'

export function usePlanningDebug() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (task: string) => debugPlanning(task),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['planning-sessions'] })
    },
  })
}

export function usePlanningSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['planning-session', sessionId],
    queryFn: () => fetchPlanningSession(sessionId!),
    enabled: !!sessionId,
  })
}

export function usePlanningSessions() {
  return useQuery({
    queryKey: ['planning-sessions'],
    queryFn: fetchPlanningSessions,
    refetchInterval: 10000,
  })
}