import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAgentRegistry,
  registerAgent,
  sendHeartbeat,
  disableAgent,
  enableAgent,
  fetchAgentRuntime,
} from "../api/agentLifecycle";

export const useAgentRegistry = () =>
  useQuery({
    queryKey: ["agents", "registry"],
    queryFn: fetchAgentRegistry,
    refetchInterval: 15000,
  });

export const useAgentRuntime = (agentId: string) =>
  useQuery({
    queryKey: ["agents", "runtime", agentId],
    queryFn: () => fetchAgentRuntime(agentId),
    enabled: !!agentId,
    refetchInterval: 10000,
  });

export const useRegisterAgent = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, capabilities }: { agentId: string; capabilities: string[] }) =>
      registerAgent(agentId, capabilities),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", "registry"] }),
  });
};

export const useHeartbeat = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => sendHeartbeat(agentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents", "registry"] }),
  });
};

export const useDisableAgent = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => disableAgent(agentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents", "registry"] });
      qc.invalidateQueries({ queryKey: ["agents", "runtime"] });
    },
  });
};

export const useEnableAgent = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => enableAgent(agentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents", "registry"] });
      qc.invalidateQueries({ queryKey: ["agents", "runtime"] });
    },
  });
};