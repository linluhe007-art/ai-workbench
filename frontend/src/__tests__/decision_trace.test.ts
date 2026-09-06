import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchTraces, fetchTaskTrace, fetchPrompts, fetchAIUsage, fetchAISummary } from "../api/aiDebug"
import type { TracesResponse, PromptsResponse, AIUsageResponse, AISummaryResponse } from "../api/aiDebug"
import { useTraces, useDebugPrompts, useAISummary } from "../hooks/useAIDebug"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseTraces: TracesResponse = {
  success: true, total: 2,
  traces: [
    { id: "t1", user_id: "u1", task_id: "task-1", trace_type: "command_analysis", component: "classifier", input_data: {}, decision: {}, reason: "Match", confidence: 0.8, metadata: {}, created_at: "2026-01-01T00:00:00" },
    { id: "t2", user_id: "u1", task_id: "task-1", trace_type: "plan_generation", component: "planner", input_data: {}, decision: {}, reason: "DAG", confidence: 0.9, metadata: {}, created_at: "2026-01-01T00:00:01" },
  ],
}

const baseSummary: AISummaryResponse = {
  success: true, summary: { total_records: 5, total_tokens: 500, total_cost: 0.01, average_latency_ms: 150, model_usage: { llama3: 3, mistral: 2 } },
}

// ===== Trace API Tests (20 tests) =====
describe("Trace API", () => {
  it("fetchTraces returns traces", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(res.traces).toHaveLength(2)
  })
  it("fetchTraces with task_id filter", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces({ task_id: "task-1" })
    expect(mockGet).toHaveBeenCalled()
  })
  it("fetchTaskTrace returns per-task traces", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTaskTrace("task-1")
    expect(res.total).toBe(2)
  })
  it("fetchPrompts returns prompts", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "test", version: 1, content: "Hi", variables: [], description: "", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts).toHaveLength(1)
  })
  it("fetchAIUsage returns records", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "llama3", provider: "ollama", tokens_input: 100, tokens_output: 50, latency_ms: 200, cost: 0, task_id: "", agent_id: "", created_at: "" }] } })
    const res = await fetchAIUsage()
    expect(res.records).toHaveLength(1)
  })
  it("fetchAISummary returns summary", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.total_tokens).toBe(500)
  })
  it("fetchAISummary has model_usage", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.model_usage.llama3).toBe(3)
  })
  it("trace has all required fields", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    for (const t of res.traces) {
      expect(typeof t.id).toBe("string")
      expect(typeof t.trace_type).toBe("string")
      expect(typeof t.component).toBe("string")
      expect(typeof t.confidence).toBe("number")
    }
  })
  it("trace confidence between 0 and 1", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    for (const t of res.traces) {
      expect(t.confidence).toBeGreaterThanOrEqual(0)
      expect(t.confidence).toBeLessThanOrEqual(1)
    }
  })
  it("summary total_cost is number", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(typeof res.summary.total_cost).toBe("number")
  })
})

describe("Trace Hook Tests", () => {
  it("useTraces returns data", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const { result } = renderHook(() => useTraces(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.traces).toHaveLength(2)
  })
  it("useTraces handles loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useTraces(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
  it("useTraces handles error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useTraces(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
  it("useAISummary returns data", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const { result } = renderHook(() => useAISummary(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.summary.total_records).toBe(5)
  })
  it("useDebugPrompts returns data", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "p", version: 1, content: "c", variables: [], description: "", active: true, created_at: "" }], total: 1 } })
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })

  it("trace types are valid strings", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    const validTypes = ["command_analysis", "plan_generation", "memory_retrieval", "agent_selection", "workflow_selection", "tool_selection", "final_result"]
    for (const t of res.traces) {
      expect(validTypes).toContain(t.trace_type)
    }
  })

  it("trace reason is non-empty when provided", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    for (const t of res.traces) {
      expect(t.reason.length).toBeGreaterThan(0)
    }
  })

  it("summary average_latency_ms is non-negative", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.average_latency_ms).toBeGreaterThanOrEqual(0)
  })

  it("summary model_usage is object", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(typeof res.summary.model_usage).toBe("object")
  })

  it("usage record has all fields", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "m", provider: "p", tokens_input: 10, tokens_output: 5, latency_ms: 100, cost: 0, task_id: "t1", agent_id: "a1", created_at: "2026-01-01T00:00:00" }] } })
    const res = await fetchAIUsage()
    const r = res.records[0]
    expect(typeof r.model).toBe("string")
    expect(typeof r.tokens_input).toBe("number")
    expect(typeof r.latency_ms).toBe("number")
  })
})

describe("Trace Edge Cases", () => {
  it("traces empty list", async () => {
    mockGet.mockResolvedValue({ data: { success: true, traces: [], total: 0 } })
    const res = await fetchTraces()
    expect(res.traces).toHaveLength(0)
  })
  it("traces with multiple filters", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces({ task_id: "t1", component: "planner", trace_type: "plan_generation" })
    expect(mockGet).toHaveBeenCalled()
  })
  it("fetchTaskTrace calls correct endpoint", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTaskTrace("my-task")
    expect(mockGet).toHaveBeenCalledWith("/intelligence/tasks/my-task/decision-trace")
  })
  it("prompt has version field", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "p", version: 3, content: "c", variables: [], description: "", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].version).toBe(3)
  })
  it("prompt active field is boolean", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "p", version: 1, content: "c", variables: [], description: "", active: false, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].active).toBe(false)
  })
  it("usage record cost is number", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "m", provider: "p", tokens_input: 1, tokens_output: 1, latency_ms: 0, cost: 0.005, task_id: "", agent_id: "", created_at: "" }] } })
    const res = await fetchAIUsage()
    expect(res.records[0].cost).toBe(0.005)
  })
  it("summary total_records is integer", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(Number.isInteger(res.summary.total_records)).toBe(true)
  })
  it("trace created_at is ISO", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(res.traces[0].created_at).toContain("T")
  })
  it("useTraces with no params works", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const { result } = renderHook(() => useTraces(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
  it("summary total_records is 0 when empty", async () => {
    mockGet.mockResolvedValue({ data: { success: true, summary: { total_records: 0, total_tokens: 0, total_cost: 0, average_latency_ms: 0, model_usage: {} } } })
    const res = await fetchAISummary()
    expect(res.summary.total_records).toBe(0)
  })
})

describe("Trace Additional", () => {
  it("traces total matches array length", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(res.total).toBe(res.traces.length)
  })
  it("trace metadata is object", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(typeof res.traces[0].metadata).toBe("object")
  })
  it("trace input_data is object", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(typeof res.traces[0].input_data).toBe("object")
  })
  it("trace decision is object", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(typeof res.traces[0].decision).toBe("object")
  })
  it("prompts total matches length", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "a", name: "a", version: 1, content: "c", variables: [], description: "", active: true, created_at: "" }, { id: "b", name: "b", version: 1, content: "c", variables: [], description: "", active: true, created_at: "" }], total: 2 } })
    const res = await fetchPrompts()
    expect(res.total).toBe(2)
  })
  it("usage records empty", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [] } })
    const res = await fetchAIUsage()
    expect(res.records).toHaveLength(0)
  })
  it("prompt variables is array", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "p", version: 1, content: "{{x}}", variables: ["x"], description: "", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(Array.isArray(res.prompts[0].variables)).toBe(true)
  })
  it("prompt description is string", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "p", version: 1, content: "c", variables: [], description: "A test prompt", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].description).toBe("A test prompt")
  })
  it("usage record provider is string", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "m", provider: "ollama", tokens_input: 10, tokens_output: 5, latency_ms: 100, cost: 0, task_id: "", agent_id: "", created_at: "" }] } })
    const res = await fetchAIUsage()
    expect(res.records[0].provider).toBe("ollama")
  })
  it("fetchTraces default params", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces()
    expect(mockGet).toHaveBeenCalledTimes(1)
  })
})
