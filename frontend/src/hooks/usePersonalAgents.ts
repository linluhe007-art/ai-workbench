import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchPersonalAgents, selectAgent, fetchDelegations, fetchAgentRoles } from "../api/personalAgents"

export const usePersonalAgents = () =>
  useQuery({ queryKey: ["personal-agents"], queryFn: fetchPersonalAgents, refetchInterval: 30000 })

export const useDelegations = () =>
  useQuery({ queryKey: ["personal-agents", "delegations"], queryFn: () => fetchDelegations() })

export const useAgentRoles = () =>
  useQuery({ queryKey: ["personal-agents", "roles"], queryFn: fetchAgentRoles, staleTime: 60000 })

export const useSelectAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { taskType: string; capabilities?: string[]; taskDescription?: string }) =>
      selectAgent(params.taskType, params.capabilities, params.taskDescription),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["personal-agents"] }),
  })
}
