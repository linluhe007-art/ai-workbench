import { useQuery } from "@tanstack/react-query";
import { fetchMetrics, fetchTaskMetrics, fetchAgentMetrics } from "../api/metrics";

export const useMetrics = () =>
  useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 15000,
  });

export const useTaskMetrics = () =>
  useQuery({
    queryKey: ["metrics", "tasks"],
    queryFn: fetchTaskMetrics,
    refetchInterval: 30000,
  });

export const useAgentMetrics = () =>
  useQuery({
    queryKey: ["metrics", "agents"],
    queryFn: fetchAgentMetrics,
    refetchInterval: 30000,
  });