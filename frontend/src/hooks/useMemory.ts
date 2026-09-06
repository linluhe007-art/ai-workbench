import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  searchMemory,
  saveMemory,
  getMemory,
  updateMemory,
  deleteMemory,
  getMemoryStats,
  getMemoryByType,
  getProfile,
  getPreferences,
  type SearchMemoryRequest,
  type SaveMemoryRequest,
} from "../api/memory"

export const useMemorySearch = (req: SearchMemoryRequest) =>
  useQuery({
    queryKey: ["memory", "search", req],
    queryFn: () => searchMemory(req),
    enabled: !!(req.query || req.memory_type || (req.tags && req.tags.length > 0)),
  })

export const useMemoryStats = () =>
  useQuery({
    queryKey: ["memory", "stats"],
    queryFn: getMemoryStats,
    refetchInterval: 15000,
  })

export const useMemoryByType = (memoryType: string) =>
  useQuery({
    queryKey: ["memory", "type", memoryType],
    queryFn: () => getMemoryByType(memoryType),
  })

export const useMemoryDetail = (id: string) =>
  useQuery({
    queryKey: ["memory", "detail", id],
    queryFn: () => getMemory(id),
    enabled: !!id,
  })

export const useProfile = () =>
  useQuery({
    queryKey: ["memory", "profile"],
    queryFn: getProfile,
  })

export const usePreferences = () =>
  useQuery({
    queryKey: ["memory", "preferences"],
    queryFn: getPreferences,
  })

export const useSaveMemory = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: SaveMemoryRequest) => saveMemory(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory"] })
    },
  })
}

export const useUpdateMemory = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SaveMemoryRequest> }) =>
      updateMemory(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory"] })
    },
  })
}

export const useDeleteMemory = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteMemory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory"] })
    },
  })
}
