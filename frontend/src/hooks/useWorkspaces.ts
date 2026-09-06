import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listWorkspaceItems, getWorkspaceItem, deleteWorkspaceItem } from '../api/workspaces'

export function useWorkspaceItems(workspaceId: string | null) {
  return useQuery({
    queryKey: ['workspace-items', workspaceId],
    queryFn: () => listWorkspaceItems(workspaceId!),
    enabled: !!workspaceId,
    refetchInterval: 5000,
  })
}

export function useWorkspaceItem(workspaceId: string | null, itemId: string | null) {
  return useQuery({
    queryKey: ['workspace-item', workspaceId, itemId],
    queryFn: () => getWorkspaceItem(workspaceId!, itemId!),
    enabled: !!workspaceId && !!itemId,
  })
}

export function useDeleteWorkspaceItem(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => deleteWorkspaceItem(workspaceId, itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-items', workspaceId] })
    },
  })
}