import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchOSStatus, fetchOSInsights, processIntent } from '../api/os'

export function useOSStatus() {
  return useQuery({
    queryKey: ['os-status'],
    queryFn: fetchOSStatus,
    refetchInterval: 15000,
  })
}

export function useOSInsights() {
  return useQuery({
    queryKey: ['os-insights'],
    queryFn: fetchOSInsights,
    refetchInterval: 30000,
  })
}

export function useProcessIntent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ intent, taskCategory }: { intent: string; taskCategory?: string }) =>
      processIntent(intent, taskCategory),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['os-status'] })
      qc.invalidateQueries({ queryKey: ['os-insights'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}
