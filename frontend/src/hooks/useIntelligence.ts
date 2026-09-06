import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { processCommand, fetchCommandHistory } from "../api/intelligence"

export const useCommandHistory = () =>
  useQuery({ queryKey: ["intelligence", "history"], queryFn: fetchCommandHistory, refetchInterval: 15000 })

export const useProcessCommand = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (prompt: string) => processCommand(prompt),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intelligence", "history"] }),
  })
}