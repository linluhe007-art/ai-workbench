import { useQuery } from '@tanstack/react-query'
import {
  fetchAuditRecords,
  fetchTaskAuditTrail,
  fetchAgentAudit,
  fetchAuditStats,
} from '../api/audit'
import type { AuditQueryParams } from '../api/audit'

export function useAuditRecords(params: AuditQueryParams = {}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn: () => fetchAuditRecords(params),
    placeholderData: (prev) => prev,
  })
}

export function useTaskAuditTrail(taskId: string | null) {
  return useQuery({
    queryKey: ['audit-trail', taskId],
    queryFn: () => fetchTaskAuditTrail(taskId!),
    enabled: !!taskId,
  })
}

export function useAgentAudit(agentId: string | null) {
  return useQuery({
    queryKey: ['audit-agent', agentId],
    queryFn: () => fetchAgentAudit(agentId!),
    enabled: !!agentId,
  })
}

export function useAuditStats() {
  return useQuery({
    queryKey: ['audit-stats'],
    queryFn: fetchAuditStats,
    refetchInterval: 30000,
  })
}