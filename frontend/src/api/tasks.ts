import apiClient from './client'
import type { TaskRecord, TaskCreateRequest, TaskCreateResponse, TraceResponse } from '../types'

export async function fetchTasks(): Promise<TaskRecord[]> {
  const { data } = await apiClient.get('/tasks')
  return data.tasks
}

export async function createTask(req: TaskCreateRequest): Promise<TaskCreateResponse> {
  const { data } = await apiClient.post('/tasks', req)
  return data
}

export async function fetchTask(taskId: string): Promise<TaskRecord> {
  const { data } = await apiClient.get(`/tasks/${taskId}`)
  return data
}

export async function fetchTaskTrace(taskId: string): Promise<TraceResponse> {
  const { data } = await apiClient.get(`/tasks/${taskId}/trace`)
  return data
}

export async function fetchTaskHistory(taskId: string) {
  const { data } = await apiClient.get(`/tasks/${taskId}/history`)
  return data
}

export async function cancelTask(taskId: string) {
  const { data } = await apiClient.post(`/tasks/${taskId}/cancel`)
  return data
}

export async function pauseTask(taskId: string) {
  const { data } = await apiClient.post(`/tasks/${taskId}/pause`)
  return data
}

export async function resumeTask(taskId: string) {
  const { data } = await apiClient.post(`/tasks/${taskId}/resume`)
  return data
}

export async function retryTask(taskId: string) {
  const { data } = await apiClient.post(`/tasks/${taskId}/retry`)
  return data
}

export async function fetchQueueStatus() {
  const { data } = await apiClient.get('/tasks/queue/status')
  return data
}