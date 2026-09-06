import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  searchExperience,
  submitFeedback,
  fetchExperienceStats,
  fetchRecommendations,
} from "../api/experience"

export const useExperienceSearch = (q: string, success?: boolean) =>
  useQuery({
    queryKey: ["experience", "search", q, success],
    queryFn: () => searchExperience(q, success),
    enabled: q.length > 0,
  })

export const useExperienceStats = () =>
  useQuery({
    queryKey: ["experience", "stats"],
    queryFn: fetchExperienceStats,
    refetchInterval: 30000,
  })

export const useRecommendations = (taskPattern: string) =>
  useQuery({
    queryKey: ["experience", "recommendations", taskPattern],
    queryFn: () => fetchRecommendations(taskPattern),
    enabled: taskPattern.length > 0,
  })

export const useSubmitFeedback = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, rating, comment, taskPattern }: { taskId: string; rating: number; comment?: string; taskPattern?: string }) =>
      submitFeedback(taskId, rating, comment || "", taskPattern || ""),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experience", "stats"] }),
  })
}