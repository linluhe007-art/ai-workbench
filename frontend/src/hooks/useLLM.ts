import { useMutation, useQuery } from '@tanstack/react-query'
import { fetchLLMConfig, testLLM } from '../api/llm'
import type { LLMTestRequest } from '../api/llm'

export function useLLMConfig() {
  return useQuery({
    queryKey: ['llm-config'],
    queryFn: fetchLLMConfig,
    refetchInterval: 60000,
  })
}

export function useLLMTest() {
  return useMutation({
    mutationFn: (req: LLMTestRequest) => testLLM(req),
  })
}
