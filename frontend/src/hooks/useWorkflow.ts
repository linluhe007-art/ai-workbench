import { useQuery } from '@tanstack/react-query'
import { fetchWorkflow } from '../api/workflows'

export function useWorkflow(taskId: string | null) {
  return useQuery({
    queryKey: ['workflow', taskId],
    queryFn: () => fetchWorkflow(taskId!),
    enabled: !!taskId,
    refetchInterval: 5000,
  })
}