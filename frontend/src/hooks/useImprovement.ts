import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchImprovementReport,
  applyImprovement,
  fetchImprovementHistory,
  revertImprovement,
} from '../api/improvement'

export function useImprovementReport() {
  return useQuery({
    queryKey: ['improvement-report'],
    queryFn: fetchImprovementReport,
    refetchInterval: 60000,
  })
}

export function useApplyImprovement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => applyImprovement(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['improvement-report'] })
      qc.invalidateQueries({ queryKey: ['improvement-history'] })
    },
  })
}

export function useImprovementHistory() {
  return useQuery({
    queryKey: ['improvement-history'],
    queryFn: fetchImprovementHistory,
    refetchInterval: 30000,
  })
}

export function useRevertImprovement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => revertImprovement(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['improvement-history'] })
    },
  })
}
