import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchModels,
  fetchProviders,
  configureModel,
  testModel,
  generateWithModel,
} from '../api/models'
import type { ConfigureRequest, GenerateRequest } from '../api/models'

export function useModels() {
  return useQuery({
    queryKey: ['models-list'],
    queryFn: fetchModels,
    refetchInterval: 60000,
  })
}

export function useProviders() {
  return useQuery({
    queryKey: ['models-providers'],
    queryFn: fetchProviders,
  })
}

export function useConfigureModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: ConfigureRequest) => configureModel(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['models-list'] })
    },
  })
}

export function useTestModel() {
  return useMutation({
    mutationFn: (providerType: string) => testModel(providerType),
  })
}

export function useGenerateWithModel() {
  return useMutation({
    mutationFn: (req: GenerateRequest) => generateWithModel(req),
  })
}
