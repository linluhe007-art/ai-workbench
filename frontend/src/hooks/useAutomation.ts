import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAutomations,
  createAutomation,
  fetchAutomation,
  runAutomation,
  updateAutomationStatus,
  deleteAutomation,
  fetchAutomationLogs,
} from '../api/automation'
import type { CreateAutomationRequest } from '../api/automation'

export function useAutomations() {
  return useQuery({
    queryKey: ['automations'],
    queryFn: fetchAutomations,
    refetchInterval: 10000,
  })
}

export function useAutomation(id: string | null) {
  return useQuery({
    queryKey: ['automation', id],
    queryFn: () => fetchAutomation(id!),
    enabled: !!id,
  })
}

export function useCreateAutomation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: CreateAutomationRequest) => createAutomation(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automations'] })
    },
  })
}

export function useRunAutomation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => runAutomation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automations'] })
    },
  })
}

export function useUpdateAutomationStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateAutomationStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automations'] })
    },
  })
}

export function useDeleteAutomation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAutomation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automations'] })
    },
  })
}

export function useAutomationLogs(id: string | null, limit = 50) {
  return useQuery({
    queryKey: ['automation-logs', id, limit],
    queryFn: () => fetchAutomationLogs(id!, limit),
    enabled: !!id,
    refetchInterval: 10000,
  })
}
