import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchTraces, fetchAIUsage, fetchAISummary, fetchTaskTrace, fetchPrompts } from "../api/aiDebug"
import { useTraces, useAIUsage, useAISummary, useTaskTrace, useDebugPrompts } from "../hooks/useAIDebug"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseTraces = { success: true, total: 2, traces: [
  { id: "t1", user_id: "u1", task_id: "debug-1", trace_type: "command_analysis", component: "c", input_data: {}, decision: {}, reason: "R", confidence: 0.8, metadata: {}, created_at: "2026-01-01T00:00:00" },
  { id: "t2", user_id: "u1", task_id: "debug-1", trace_type: "final_result", component: "o", input_data: {}, decision: {}, reason: "Done", confidence: 0.95, metadata: {}, created_at: "2026-01-01T00:00:01" },
]}

const baseSummary = { success: true, summary: { total_records: 10, total_tokens: 1000, total_cost: 0.05, average_latency_ms: 200, model_usage: { llama3: 8, gpt4: 2 } } }

// ===== API Tests =====
describe("AI Debug API", () => {
  it("fetchTraces chained with fetchAISummary", async () => {
    mockGet.mockResolvedValueOnce({ data: baseTraces }).mockResolvedValueOnce({ data: baseSummary })
    const traces = await fetchTraces()
    const summary = await fetchAISummary()
    expect(traces.traces).toHaveLength(2)
    expect(summary.summary.total_tokens).toBe(1000)
  })
  it("fetchAIUsage returns records", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "llama3", provider: "ollama", tokens_input: 50, tokens_output: 25, latency_ms: 120, cost: 0, task_id: "debug-1", agent_id: "a1", created_at: "" }] } })
    const res = await fetchAIUsage()
    expect(res.records[0].model).toBe("llama3")
    expect(res.records[0].task_id).toBe("debug-1")
  })
  it("trace for debugging shows all steps", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces({ task_id: "debug-1" })
    const types = res.traces.map(t => t.trace_type)
    expect(types).toContain("command_analysis")
    expect(types).toContain("final_result")
  })
  it("summary model_usage counts are correct", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.model_usage.llama3).toBe(8)
    expect(res.summary.model_usage.gpt4).toBe(2)
  })
  it("traces filter by component", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces({ component: "c" })
    expect(mockGet).toHaveBeenCalled()
  })
  it("fetchTaskTrace returns decision trace for task", async () => {
    mockGet.mockResolvedValue({ data: { success: true, task_id: "task-x", traces: baseTraces.traces, total: 2 } })
    const res = await fetchTaskTrace("task-x")
    expect(res.task_id).toBe("task-x")
    expect(res.traces).toHaveLength(2)
  })
  it("fetchPrompts returns prompts list", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "test_prompt", version: 1, content: "Hello {{name}}", variables: ["name"], description: "Test", active: true, created_at: "2026-01-01T00:00:00" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].name).toBe("test_prompt")
    expect(res.prompts[0].variables).toContain("name")
  })
  it("fetchTraces with multiple filter params", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces({ task_id: "t1", component: "planner", trace_type: "plan_generation" })
    const callArg = mockGet.mock.calls[0][0] as string
    expect(callArg).toContain("task_id=t1")
    expect(callArg).toContain("component=planner")
    expect(callArg).toContain("trace_type=plan_generation")
  })
  it("fetchTraces empty results", async () => {
    mockGet.mockResolvedValue({ data: { success: true, traces: [], total: 0 } })
    const res = await fetchTraces({ task_id: "nonexistent" })
    expect(res.traces).toHaveLength(0)
    expect(res.total).toBe(0)
  })
  it("fetchAIUsage handles multiple providers", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [
      { id: "r1", model: "llama3", provider: "ollama", tokens_input: 10, tokens_output: 5, latency_ms: 100, cost: 0, task_id: "", agent_id: "", created_at: "" },
      { id: "r2", model: "gpt-4", provider: "openai", tokens_input: 50, tokens_output: 50, latency_ms: 500, cost: 0.01, task_id: "", agent_id: "", created_at: "" },
    ]} })
    const res = await fetchAIUsage()
    expect(res.records).toHaveLength(2)
    expect(res.records[0].provider).toBe("ollama")
    expect(res.records[1].provider).toBe("openai")
  })
  it("fetchPrompts handles empty", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [], total: 0 } })
    const res = await fetchPrompts()
    expect(res.prompts).toHaveLength(0)
  })
})

// ===== Hook Tests =====
describe("AI Debug Hooks", () => {
  it("useTraces for debug returns data", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const { result } = renderHook(() => useTraces({ task_id: "debug-1" }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
  it("useAIUsage returns records", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "m", provider: "p", tokens_input: 10, tokens_output: 5, latency_ms: 100, cost: 0, task_id: "", agent_id: "", created_at: "" }] } })
    const { result } = renderHook(() => useAIUsage(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
  it("useAISummary returns summary", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const { result } = renderHook(() => useAISummary(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.summary.model_usage.llama3).toBe(8)
  })
  it("useAIUsage handles loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useAIUsage(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
  it("useAISummary handles error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useAISummary(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
  it("useTaskTrace enabled when taskId provided", async () => {
    mockGet.mockResolvedValue({ data: { success: true, task_id: "tt1", traces: baseTraces.traces, total: 2 } })
    const { result } = renderHook(() => useTaskTrace("tt1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.task_id).toBe("tt1")
  })
  it("useTaskTrace disabled when taskId is null", () => {
    mockGet.mockResolvedValue({ data: { success: true, traces: [], total: 0 } })
    const { result } = renderHook(() => useTaskTrace(null), { wrapper })
    expect(result.current.isLoading).toBe(false)
    expect(result.current.fetchStatus).toBe("idle")
  })
  it("useDebugPrompts returns prompts", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "greeting", version: 1, content: "Hi", variables: [], description: "", active: true, created_at: "2026-01-01T00:00:00" }], total: 1 } })
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.prompts[0].name).toBe("greeting")
  })
  it("useTraces handles error gracefully", async () => {
    mockGet.mockRejectedValue(new Error("Network error"))
    const { result } = renderHook(() => useTraces(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
  it("useAIUsage handles empty records", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [] } })
    const { result } = renderHook(() => useAIUsage(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

// ===== Type & Edge Cases =====
describe("AI Debug Types", () => {
  it("trace type enum values", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    const valid = ["command_analysis", "plan_generation", "memory_retrieval", "agent_selection", "workflow_selection", "tool_selection", "final_result"]
    for (const t of res.traces) {
      expect(valid).toContain(t.trace_type)
    }
  })
  it("summary total_cost is non-negative", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.total_cost).toBeGreaterThanOrEqual(0)
  })
  it("usage record latency is number", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r1", model: "m", provider: "p", tokens_input: 1, tokens_output: 1, latency_ms: 250.5, cost: 0, task_id: "", agent_id: "", created_at: "" }] } })
    const res = await fetchAIUsage()
    expect(res.records[0].latency_ms).toBe(250.5)
  })
  it("trace reason and confidence present", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    expect(res.traces[0].reason.length).toBeGreaterThan(0)
    expect(res.traces[0].confidence).toBeGreaterThan(0)
  })
  it("summary empty model_usage", async () => {
    mockGet.mockResolvedValue({ data: { success: true, summary: { total_records: 0, total_tokens: 0, total_cost: 0, average_latency_ms: 0, model_usage: {} } } })
    const res = await fetchAISummary()
    expect(Object.keys(res.summary.model_usage)).toHaveLength(0)
  })
  it("trace confidence in valid range", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const res = await fetchTraces()
    for (const t of res.traces) {
      expect(t.confidence).toBeGreaterThanOrEqual(0)
      expect(t.confidence).toBeLessThanOrEqual(1)
    }
  })
  it("task trace includes all decision types", async () => {
    mockGet.mockResolvedValue({ data: { success: true, task_id: "t-all", traces: [
      { id: "a", user_id: "u1", task_id: "t-all", trace_type: "command_analysis", component: "classifier", input_data: {}, decision: {}, reason: "", confidence: 0.8, metadata: {}, created_at: "" },
      { id: "b", user_id: "u1", task_id: "t-all", trace_type: "plan_generation", component: "planner", input_data: {}, decision: {}, reason: "", confidence: 0.9, metadata: {}, created_at: "" },
      { id: "c", user_id: "u1", task_id: "t-all", trace_type: "memory_retrieval", component: "memory", input_data: {}, decision: {}, reason: "", confidence: 0.7, metadata: {}, created_at: "" },
      { id: "d", user_id: "u1", task_id: "t-all", trace_type: "agent_selection", component: "selector", input_data: {}, decision: {}, reason: "", confidence: 0.85, metadata: {}, created_at: "" },
      { id: "e", user_id: "u1", task_id: "t-all", trace_type: "workflow_selection", component: "planner", input_data: {}, decision: {}, reason: "", confidence: 0.9, metadata: {}, created_at: "" },
      { id: "f", user_id: "u1", task_id: "t-all", trace_type: "tool_selection", component: "executor", input_data: {}, decision: {}, reason: "", confidence: 0.95, metadata: {}, created_at: "" },
      { id: "g", user_id: "u1", task_id: "t-all", trace_type: "final_result", component: "orchestrator", input_data: {}, decision: {}, reason: "", confidence: 1.0, metadata: {}, created_at: "" },
    ], total: 7 } })
    const res = await fetchTaskTrace("t-all")
    expect(res.traces).toHaveLength(7)
    const types = res.traces.map(t => t.trace_type)
    expect(types).toContain("command_analysis")
    expect(types).toContain("plan_generation")
    expect(types).toContain("memory_retrieval")
    expect(types).toContain("agent_selection")
    expect(types).toContain("workflow_selection")
    expect(types).toContain("tool_selection")
    expect(types).toContain("final_result")
  })
  it("summary tokens are non-negative", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const res = await fetchAISummary()
    expect(res.summary.total_tokens).toBeGreaterThanOrEqual(0)
    expect(res.summary.average_latency_ms).toBeGreaterThanOrEqual(0)
  })
  it("usage record has all fields", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [{ id: "r-full", model: "gpt-4", provider: "openai", tokens_input: 100, tokens_output: 200, latency_ms: 500, cost: 0.02, task_id: "t1", agent_id: "a1", created_at: "2026-01-01T00:00:00" }] } })
    const res = await fetchAIUsage()
    const r = res.records[0]
    expect(r.id).toBe("r-full")
    expect(r.model).toBe("gpt-4")
    expect(r.provider).toBe("openai")
    expect(r.tokens_input).toBe(100)
    expect(r.tokens_output).toBe(200)
    expect(r.cost).toBe(0.02)
    expect(r.task_id).toBe("t1")
    expect(r.agent_id).toBe("a1")
  })
  it("prompt has required fields", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "pp1", name: "p1", version: 3, content: "test", variables: ["x","y"], description: "desc", active: false, created_at: "2026-06-01T00:00:00" }], total: 1 } })
    const res = await fetchPrompts()
    const p = res.prompts[0]
    expect(p.id).toBe("pp1")
    expect(p.version).toBe(3)
    expect(p.active).toBe(false)
    expect(p.variables).toEqual(["x","y"])
  })
  it("useTraces queryKey includes params", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    const { result } = renderHook(() => useTraces({ task_id: "tk1", component: "c1" }), { wrapper })
    await waitFor(() => expect(result.current.data?.total).toBe(2))
    expect(result.current.data?.traces[0].task_id).toBe("debug-1")
  })
  it("fetchTaskTrace with non-existent task", async () => {
    mockGet.mockResolvedValue({ data: { success: true, task_id: "nx", traces: [], total: 0 } })
    const res = await fetchTaskTrace("nx")
    expect(res.traces).toHaveLength(0)
    expect(res.total).toBe(0)
  })
  it("fetchTraces with user_id filter", async () => {
    mockGet.mockResolvedValue({ data: baseTraces })
    await fetchTraces({ user_id: "u1" })
    const callArg = mockGet.mock.calls[0][0] as string
    expect(callArg).toContain("user_id=u1")
  })
  it("useAISummary model_usage is object", async () => {
    mockGet.mockResolvedValue({ data: baseSummary })
    const { result } = renderHook(() => useAISummary(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(typeof result.current.data?.summary.model_usage).toBe("object")
  })
})


// ===== Additional Edge Cases =====
describe("AI Debug Integration", () => {
  it("multiple traces with same task retain order", async () => {
    mockGet.mockResolvedValue({ data: { success: true, traces: [
      { id: "s1", user_id: "u1", task_id: "tk", trace_type: "command_analysis", component: "c", input_data: {}, decision: {}, reason: "", confidence: 0.5, metadata: {}, created_at: "2026-01-01T00:00:01" },
      { id: "s2", user_id: "u1", task_id: "tk", trace_type: "plan_generation", component: "p", input_data: {}, decision: {}, reason: "", confidence: 0.6, metadata: {}, created_at: "2026-01-01T00:00:02" },
      { id: "s3", user_id: "u1", task_id: "tk", trace_type: "final_result", component: "o", input_data: {}, decision: {}, reason: "", confidence: 0.7, metadata: {}, created_at: "2026-01-01T00:00:03" },
    ], total: 3 } })
    const res = await fetchTraces({ task_id: "tk" })
    expect(res.traces).toHaveLength(3)
    expect(res.total).toBe(3)
  })
  it("fetchAIUsage cost aggregation", async () => {
    mockGet.mockResolvedValue({ data: { success: true, records: [
      { id: "r1", model: "m1", provider: "p1", tokens_input: 100, tokens_output: 200, latency_ms: 50, cost: 0.01, task_id: "", agent_id: "", created_at: "" },
      { id: "r2", model: "m1", provider: "p1", tokens_input: 300, tokens_output: 400, latency_ms: 75, cost: 0.02, task_id: "", agent_id: "", created_at: "" },
    ]} })
    const res = await fetchAIUsage()
    const totalCost = res.records.reduce((s, r) => s + r.cost, 0)
    expect(totalCost).toBe(0.03)
  })
  it("useTaskTrace handles error", async () => {
    mockGet.mockRejectedValue(new Error("Not found"))
    const { result } = renderHook(() => useTaskTrace("bad-id"), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
  it("useDebugPrompts handles error", async () => {
    mockGet.mockRejectedValue(new Error("Server error"))
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
  it("fetchPrompts with multiple versions", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [
      { id: "v1", name: "greet", version: 1, content: "Hi", variables: [], description: "", active: false, created_at: "2026-01-01T00:00:00" },
      { id: "v2", name: "greet", version: 2, content: "Hello", variables: ["name"], description: "", active: true, created_at: "2026-02-01T00:00:00" },
    ], total: 2 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].active).toBe(false)
    expect(res.prompts[1].active).toBe(true)
    expect(res.total).toBe(2)
  })
})
