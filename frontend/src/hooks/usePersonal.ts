import { useQuery } from '@tanstack/react-query'
import { fetchPersonalDashboard } from '../api/personal'

export function usePersonalDashboard() {
  return useQuery({
    queryKey: ['personal-dashboard'],
    queryFn: fetchPersonalDashboard,
    refetchInterval: 30000,
    staleTime: 10000,
  })
}
