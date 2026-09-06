import { useQuery } from "@tanstack/react-query"
import { fetchCluster } from "../api/deployment"

export const useCluster = () =>
  useQuery({
    queryKey: ["deployment", "cluster"],
    queryFn: fetchCluster,
    refetchInterval: 10000,
  })