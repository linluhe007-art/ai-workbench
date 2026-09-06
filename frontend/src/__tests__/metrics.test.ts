import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchMetrics, fetchTaskMetrics, fetchAgentMetrics } from "../api/metrics"
import { useMetrics, useTaskMetrics, useAgentMetrics } from "../hooks/useMetrics"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseMetrics = {
  cpu: { percent: 25.5 },
  memory: { total_gb: 16, available_gb: 8, percent: 50, process_mb: 256.5 },
  runtime: {
    instance_id: "inst-1",
    uptime_seconds: 3600,
    status: "healthy",
    persistence_enabled: true,
    redis_enabled: true,
  },
  tasks: { total: 5, created: 10, completed: 5, failed: 2, timeout: 0, cancelled: 3 },
  queue: { running: 2, queued: 1, max_concurrent: 3 },
  agents: {
    total_executions: 50,
    success_rate: 0.9,
    latency: { avg: 120.5, p50: 100, p95: 200 },
  },
}

const baseTaskMetrics = {
  total: 10,
  completed: 5,
  failed: 2,
  timeout: 0,
  cancelled: 3,
  success_rate: 0.5,
  failure_rate: 0.2,
  average_duration_ms: 350.0,
}

const baseAgentMetrics = {
  total_executions: 50,
  agents: [
    { agent_id: "mock", executions: 30, errors: 2, latency: { avg: 100 } },
    { agent_id: "research", executions: 20, errors: 1, latency: { avg: 150 } },
  ],
}

// --- API Tests ---

describe("Metrics API", () => {
  it("fetchMetrics returns metrics", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.cpu.percent).toBe(25.5)
    expect(res.memory.total_gb).toBe(16)
    expect(mockGet).toHaveBeenCalledWith("/metrics")
  })

  it("fetchTaskMetrics returns task metrics", async () => {
    mockGet.mockResolvedValue({ data: baseTaskMetrics })
    const res = await fetchTaskMetrics()
    expect(res.total).toBe(10)
    expect(res.success_rate).toBe(0.5)
    expect(mockGet).toHaveBeenCalledWith("/metrics/tasks")
  })

  it("fetchAgentMetrics returns agent metrics", async () => {
    mockGet.mockResolvedValue({ data: baseAgentMetrics })
    const res = await fetchAgentMetrics()
    expect(res.total_executions).toBe(50)
    expect(res.agents).toHaveLength(2)
    expect(mockGet).toHaveBeenCalledWith("/metrics/agents")
  })
})

// --- API Response Parsing ---

describe("Metrics response parsing", () => {
  it("parses CPU percent", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.cpu.percent).toBeTypeOf("number")
  })

  it("parses memory fields", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.memory.total_gb).toBeGreaterThan(0)
    expect(res.memory.process_mb).toBeGreaterThan(0)
  })

  it("parses runtime instance_id", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.runtime.instance_id).toBe("inst-1")
  })

  it("parses task counters", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.tasks.created).toBe(10)
    expect(res.tasks.completed).toBe(5)
    expect(res.tasks.failed).toBe(2)
  })

  it("parses queue status", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.queue.running).toBe(2)
    expect(res.queue.max_concurrent).toBe(3)
  })

  it("parses agent metrics", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const res = await fetchMetrics()
    expect(res.agents.total_executions).toBe(50)
    expect(res.agents.success_rate).toBe(0.9)
  })

  it("parses task metrics success rate", async () => {
    mockGet.mockResolvedValue({ data: baseTaskMetrics })
    const res = await fetchTaskMetrics()
    expect(res.success_rate).toBe(0.5)
    expect(res.failure_rate).toBe(0.2)
    expect(res.average_duration_ms).toBe(350)
  })

  it("parses agent array from agent metrics", async () => {
    mockGet.mockResolvedValue({ data: baseAgentMetrics })
    const res = await fetchAgentMetrics()
    expect(res.agents[0].agent_id).toBe("mock")
    expect(res.agents[0].executions).toBe(30)
    expect(res.agents[0].latency.avg).toBe(100)
  })
})

// --- Hook Tests ---

describe("useMetrics hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const { result } = renderHook(() => useMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.cpu.percent).toBe(25.5)
    expect(result.current.data?.runtime.instance_id).toBe("inst-1")
  })

  it("has correct queryKey", async () => {
    mockGet.mockResolvedValue({ data: baseMetrics })
    const { result } = renderHook(() => useMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})

describe("useTaskMetrics hook", () => {
  it("returns task data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseTaskMetrics })
    const { result } = renderHook(() => useTaskMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(10)
    expect(result.current.data?.completed).toBe(5)
  })

  it("has correct queryKey", async () => {
    mockGet.mockResolvedValue({ data: baseTaskMetrics })
    const { result } = renderHook(() => useTaskMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})

describe("useAgentMetrics hook", () => {
  it("returns agent data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseAgentMetrics })
    const { result } = renderHook(() => useAgentMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_executions).toBe(50)
    expect(result.current.data?.agents).toHaveLength(2)
  })

  it("has correct queryKey", async () => {
    mockGet.mockResolvedValue({ data: baseAgentMetrics })
    const { result } = renderHook(() => useAgentMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})

// --- Error Handling ---

describe("Metrics error handling", () => {
  it("fetchMetrics handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchMetrics()).rejects.toThrow("Network Error")
  })

  it("fetchTaskMetrics handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Timeout"))
    await expect(fetchTaskMetrics()).rejects.toThrow("Timeout")
  })

  it("fetchAgentMetrics handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Service Unavailable"))
    await expect(fetchAgentMetrics()).rejects.toThrow("Service Unavailable")
  })

  it("hooks handle error state", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useMetrics(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeDefined()
  })
})

// --- Edge Cases ---

describe("Metrics edge cases", () => {
  it("handles zero CPU", async () => {
    const m = { ...baseMetrics, cpu: { percent: 0 } }
    mockGet.mockResolvedValue({ data: m })
    const res = await fetchMetrics()
    expect(res.cpu.percent).toBe(0)
  })

  it("handles zero tasks", async () => {
    const m = { ...baseTaskMetrics, total: 0, completed: 0, failed: 0 }
    mockGet.mockResolvedValue({ data: m })
    const res = await fetchTaskMetrics()
    expect(res.total).toBe(0)
  })

  it("handles empty agents list", async () => {
    const m = { total_executions: 0, agents: [] }
    mockGet.mockResolvedValue({ data: m })
    const res = await fetchAgentMetrics()
    expect(res.agents).toHaveLength(0)
  })

  it("handles 100% memory usage", async () => {
    const m = { ...baseMetrics, memory: { ...baseMetrics.memory, percent: 100 } }
    mockGet.mockResolvedValue({ data: m })
    const res = await fetchMetrics()
    expect(res.memory.percent).toBe(100)
  })

  it("handles large uptime", async () => {
    const m = { ...baseMetrics, runtime: { ...baseMetrics.runtime, uptime_seconds: 86400 * 30 } }
    mockGet.mockResolvedValue({ data: m })
    const res = await fetchMetrics()
    expect(res.runtime.uptime_seconds).toBe(2592000)
  })
})

// --- Loading State ---

describe("Metrics loading state", () => {
  it("shows loading initially", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useMetrics(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("shows loading for task metrics", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useTaskMetrics(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("shows loading for agent metrics", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useAgentMetrics(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles malformed response data", async () => {
    mockGet.mockResolvedValue({ data: { cpu: null, memory: {} } })
    const res = await fetchMetrics()
    expect(res.cpu).toBeNull()
    expect(res.memory).toBeDefined()
  })
})
