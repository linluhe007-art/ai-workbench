import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchTaskArtifacts, fetchArtifact, deleteArtifact, renameArtifact } from "../api/artifacts"

export function useTaskArtifacts(taskId: string | null) {
  return useQuery({
    queryKey: ["task-artifacts", taskId],
    queryFn: () => fetchTaskArtifacts(taskId!),
    enabled: !!taskId,
    refetchInterval: 10000,
  })
}

export function useArtifact(artifactId: string | null) {
  return useQuery({
    queryKey: ["artifact", artifactId],
    queryFn: () => fetchArtifact(artifactId!),
    enabled: !!artifactId,
  })
}

export function useDeleteArtifact(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (artifactId: string) => deleteArtifact(artifactId),
    onSuccess: () => {
      if (taskId) qc.invalidateQueries({ queryKey: ["task-artifacts", taskId] })
    },
  })
}

export function useRenameArtifact(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ artifactId, name }: { artifactId: string; name: string }) => renameArtifact(artifactId, name),
    onSuccess: () => {
      if (taskId) qc.invalidateQueries({ queryKey: ["task-artifacts", taskId] })
    },
  })
}