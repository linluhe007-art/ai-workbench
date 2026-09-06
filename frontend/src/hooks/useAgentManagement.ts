import { useQuery } from '@tanstack/react-query'
import { fetchAgentCapabilities, fetchAgentHealth, fetchAgentHistory, fetchAllCapabilities } from '../api/agentManagement'

export function useAgentCapabilities(agentId: string | null) {
  return useQuery({
    queryKey: ['agent-capabilities', agentId],
    queryFn: () => fetchAgentCapabilities(agentId!),
    enabled: !!agentId,
    refetchInterval: 10000,
  })
}

export function useAgentHealth(agentId: string | null) {
  return useQuery({
    queryKey: ['agent-health', agentId],
    queryFn: () => fetchAgentHealth(agentId!),
    enabled: !!agentId,
    refetchInterval: 5000,
  })
}

export function useAgentHistory(agentId: string | null) {
  return useQuery({
    queryKey: ['agent-history', agentId],
    queryFn: () => fetchAgentHistory(agentId!),
    enabled: !!agentId,
    refetchInterval: 10000,
  })
}

export function useAllCapabilities() {
  return useQuery({
    queryKey: ['all-capabilities'],
    queryFn: fetchAllCapabilities,
    refetchInterval: 15000,
  })
}