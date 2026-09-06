import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTasks, createTask, fetchTask, cancelTask, pauseTask, resumeTask, retryTask, fetchQueueStatus } from '../api/tasks'
import type { TaskCreateRequest } from '../types'

export function useTasks() {
  return useQuery({
    queryKey: ['tasks'],
    queryFn: fetchTasks,
    refetchInterval: 5000,
  })
}

export function useTask(taskId: string | null) {
  return useQuery({
    queryKey: ['task', taskId],
    queryFn: () => fetchTask(taskId!),
    enabled: !!taskId,
    refetchInterval: 3000,
  })
}

export function useCreateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: TaskCreateRequest) => createTask(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useCancelTask(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => cancelTask(taskId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task', taskId] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function usePauseTask(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => pauseTask(taskId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task', taskId] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useResumeTask(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => resumeTask(taskId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task', taskId] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useRetryTask(taskId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => retryTask(taskId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task', taskId] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useQueueStatus() {
  return useQuery({
    queryKey: ['queue-status'],
    queryFn: fetchQueueStatus,
    refetchInterval: 5000,
  })
}