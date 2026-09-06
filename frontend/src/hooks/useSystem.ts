import { useQuery } from '@tanstack/react-query'
import { fetchSystemHealth, fetchSystemInfo, fetchReadiness, fetchSystemMetrics } from '../api/system'

export const useSystemHealth = () =>
  useQuery({ queryKey: ['system', 'health'], queryFn: fetchSystemHealth, refetchInterval: 30000 })

export const useSystemInfo = () =>
  useQuery({ queryKey: ['system', 'info'], queryFn: fetchSystemInfo, refetchInterval: 30000 })

export const useReadiness = () =>
  useQuery({ queryKey: ['system', 'readiness'], queryFn: fetchReadiness, refetchInterval: 15000 })

export const useSystemMetrics = () =>
  useQuery({ queryKey: ['system', 'metrics'], queryFn: fetchSystemMetrics, refetchInterval: 30000 })
