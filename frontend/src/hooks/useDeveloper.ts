import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  createAPIKey, fetchAPIKeys, deleteAPIKey,
  createWebhook, fetchWebhooks, deleteWebhook,
} from "../api/developer"

export const useAPIKeys = () =>
  useQuery({ queryKey: ["developer", "api-keys"], queryFn: fetchAPIKeys, refetchInterval: 30000 })

export const useCreateAPIKey = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, permissions }: { name: string; permissions?: string[] }) =>
      createAPIKey(name, permissions),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["developer", "api-keys"] }),
  })
}

export const useDeleteAPIKey = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (keyId: string) => deleteAPIKey(keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["developer", "api-keys"] }),
  })
}

export const useWebhooks = () =>
  useQuery({ queryKey: ["developer", "webhooks"], queryFn: fetchWebhooks, refetchInterval: 30000 })

export const useCreateWebhook = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ url, events }: { url: string; events?: string[] }) =>
      createWebhook(url, events),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["developer", "webhooks"] }),
  })
}

export const useDeleteWebhook = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteWebhook(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["developer", "webhooks"] }),
  })
}