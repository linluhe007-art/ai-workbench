import { useQuery } from '@tanstack/react-query'
import { fetchAgents, fetchMetrics, fetchRuntimeStatus } from '../api/agents'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    refetchInterval: 10000,
  })
}

export function useMetrics() {
  return useQuery({
    queryKey: ['metrics'],
    queryFn: fetchMetrics,
    refetchInterval: 5000,
  })
}

export function useRuntimeStatus() {
  return useQuery({
    queryKey: ['runtime-status'],
    queryFn: fetchRuntimeStatus,
    refetchInterval: 10000,
  })
}