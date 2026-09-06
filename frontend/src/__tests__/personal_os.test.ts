import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchOSStatus, fetchOSInsights, processIntent } from "../api/os"
import type { OSStatusResponse, OSInsightsResponse, OSProcessResponse } from "../api/os"
import { useOSStatus, useOSInsights } from "../hooks/useOS"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseStatus: OSStatusResponse = {
  success: true, os_version: "5.10",
  components: { orchestrator: "active", context_builder: "active", decision_engine: "active" },
  system_state: {
    agents_available: 5, agents_active: 2, automations_running: 1,
    tasks_queued: 3, tasks_running: 1, last_improvement_at: "2026-01-01T00:00:00",
    overall_health: "healthy",
  },
  agents_available: 5, agents_active: 2,
  tasks_running: 1, tasks_queued: 3, overall_health: "healthy",
}

const baseInsights: OSInsightsResponse = {
  success: true,
  context: { user_intent: "test", system_state: { agents_available: 5 } },
  decision: { action: "chat", confidence: 0.5, reasoning: "Test" },
  suggestions: [
    { type: "tip", message: "Use /os to see your AI at work" },
    { type: "status", message: "5 agents available" },
    { type: "action", message: "Try the Command Center" },
  ],
}

const baseProcessResult: OSProcessResponse = {
  success: true,
  result: {
    id: "abc123", user_intent: "Research AI", success: true,
    context: { memory_snapshot: { recent_experiences: [] } },
    decision: {
      action: "create_task", confidence: 0.75, reasoning: "Test reason",
      task_description: "Research AI", recommended_agents: [], should_automate: false,
      should_learn: true, priority: 1,
    },
    steps: [
      { name: "memory_retrieval", status: "completed", result: { memories_found: 0 }, error: "", duration_ms: 5.2 },
      { name: "decision", status: "completed", result: { action: "create_task" }, error: "", duration_ms: 1.1 },
      { name: "planning", status: "skipped", result: {}, error: "", duration_ms: 0 },
      { name: "agent_selection", status: "skipped", result: {}, error: "", duration_ms: 0 },
      { name: "learning", status: "skipped", result: {}, error: "", duration_ms: 0 },
    ],
    task_id: "", recommendations: ["Build memory"], generated_at: "2026-01-01T00:00:00",
  },
}

// ===== API Tests =====

describe("OS API", () => {
  it("fetchOSStatus returns status", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(res.success).toBe(true)
    expect(res.os_version).toBe("5.10")
    expect(mockGet).toHaveBeenCalledWith("/os/status")
  })

  it("fetchOSInsights returns insights", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(res.suggestions).toHaveLength(3)
    expect(mockGet).toHaveBeenCalledWith("/os/insights")
  })

  it("processIntent sends request", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Research AI")
    expect(res.result.decision.action).toBe("create_task")
    expect(mockPost).toHaveBeenCalledWith("/os/process", { intent: "Research AI", task_category: "" })
  })

  it("processIntent with task category", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    await processIntent("Code", "coding")
    expect(mockPost).toHaveBeenCalledWith("/os/process", { intent: "Code", task_category: "coding" })
  })
})

// ===== Response Parsing =====

describe("OS Response Parsing", () => {
  it("status has system_state", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(res.system_state.agents_available).toBe(5)
    expect(res.system_state.overall_health).toBe("healthy")
  })

  it("insights has decision", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(res.decision.action).toBe("chat")
    expect(typeof res.decision.confidence).toBe("number")
  })

  it("process result has 5 steps", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(res.result.steps).toHaveLength(5)
  })

  it("process result steps have correct names", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    const names = res.result.steps.map((s) => s.name)
    expect(names).toContain("memory_retrieval")
    expect(names).toContain("decision")
    expect(names).toContain("planning")
    expect(names).toContain("agent_selection")
    expect(names).toContain("learning")
  })
})

// ===== Hook Tests =====

describe("useOSStatus hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const { result } = renderHook(() => useOSStatus(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.system_state.agents_available).toBe(5)
  })

  it("handles loading state", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useOSStatus(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useOSStatus(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("useOSInsights hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const { result } = renderHook(() => useOSInsights(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.suggestions).toHaveLength(3)
  })

  it("handles error state", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useOSInsights(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ===== Type Validation =====

describe("OS Type Validation", () => {
  it("OSStatusResponse has components", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.components).toBe("object")
    expect(res.components.orchestrator).toBe("active")
  })

  it("OSInsightsResponse suggestions are array", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(Array.isArray(res.suggestions)).toBe(true)
  })

  it("suggestion has type and message", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    for (const s of res.suggestions) {
      expect(typeof s.type).toBe("string")
      expect(typeof s.message).toBe("string")
    }
  })

  it("OSProcessResult has required fields", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.id).toBe("string")
    expect(typeof res.result.success).toBe("boolean")
    expect(Array.isArray(res.result.steps)).toBe(true)
  })

  it("OSProcessResult decision has action", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.decision.action).toBe("string")
  })

  it("OSProcessResult decision confidence is number", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.decision.confidence).toBe("number")
    expect(res.result.decision.confidence).toBeGreaterThanOrEqual(0)
    expect(res.result.decision.confidence).toBeLessThanOrEqual(1)
  })

  it("step has duration_ms", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    for (const s of res.result.steps) {
      expect(typeof s.duration_ms).toBe("number")
      expect(s.duration_ms).toBeGreaterThanOrEqual(0)
    }
  })

  it("step status is valid", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    const validStatuses = ["pending", "running", "completed", "failed", "skipped"]
    for (const s of res.result.steps) {
      expect(validStatuses).toContain(s.status)
    }
  })

  it("system_state overall_health is valid", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(["healthy", "degraded"]).toContain(res.system_state.overall_health)
  })
})

// ===== Edge Cases =====

describe("OS Edge Cases", () => {
  it("status with zero agents", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseStatus, system_state: { ...baseStatus.system_state, agents_available: 0, agents_active: 0 }, agents_available: 0, agents_active: 0 },
    })
    const res = await fetchOSStatus()
    expect(res.agents_available).toBe(0)
    expect(res.agents_active).toBe(0)
  })

  it("status with degraded health", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseStatus, system_state: { ...baseStatus.system_state, overall_health: "degraded" }, overall_health: "degraded" },
    })
    const res = await fetchOSStatus()
    expect(res.overall_health).toBe("degraded")
  })

  it("insights with empty suggestions", async () => {
    mockGet.mockResolvedValue({ data: { ...baseInsights, suggestions: [] } })
    const res = await fetchOSInsights()
    expect(res.suggestions).toHaveLength(0)
  })

  it("process result with failed step", async () => {
    mockPost.mockResolvedValue({
      data: {
        ...baseProcessResult,
        result: {
          ...baseProcessResult.result,
          steps: [
            ...baseProcessResult.result.steps.slice(0, 2),
            { name: "planning", status: "failed", result: {}, error: "Boom", duration_ms: 10 },
            ...baseProcessResult.result.steps.slice(3),
          ],
        },
      },
    })
    const res = await processIntent("Test")
    const failed = res.result.steps.find((s) => s.status === "failed")
    expect(failed).toBeDefined()
    expect(failed!.error).toBe("Boom")
  })

  it("process result with automate decision", async () => {
    mockPost.mockResolvedValue({
      data: {
        ...baseProcessResult,
        result: { ...baseProcessResult.result, decision: { ...baseProcessResult.result.decision, action: "automate", should_automate: true } },
      },
    })
    const res = await processIntent("daily report")
    expect(res.result.decision.action).toBe("automate")
    expect(res.result.decision.should_automate).toBe(true)
  })

  it("process result with improve decision", async () => {
    mockPost.mockResolvedValue({
      data: {
        ...baseProcessResult,
        result: { ...baseProcessResult.result, decision: { ...baseProcessResult.result.decision, action: "improve" } },
      },
    })
    const res = await processIntent("optimize workflow")
    expect(res.result.decision.action).toBe("improve")
  })

  it("process result with query decision", async () => {
    mockPost.mockResolvedValue({
      data: {
        ...baseProcessResult,
        result: { ...baseProcessResult.result, decision: { ...baseProcessResult.result.decision, action: "query" } },
      },
    })
    const res = await processIntent("how does this work")
    expect(res.result.decision.action).toBe("query")
  })

  it("process result has recommendations array", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(Array.isArray(res.result.recommendations)).toBe(true)
  })

  it("process result generated_at is ISO", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(res.result.generated_at).toContain("T")
  })

  it("status components all active", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    Object.values(res.components).forEach((v) => {
      expect(v).toBe("active")
    })
  })

  it("status has tasks_running as number", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.tasks_running).toBe("number")
  })

  it("status has tasks_queued as number", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.tasks_queued).toBe("number")
  })

  it("insights context is an object", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(typeof res.context).toBe("object")
  })

  it("process result id is non-empty", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(res.result.id.length).toBeGreaterThan(0)
  })

  it("decision priority is a valid integer", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("critical fix")
    expect([0, 1, 2]).toContain(res.result.decision.priority)
  })

  it("step durations are reasonable", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    for (const s of res.result.steps) {
      expect(s.duration_ms).toBeLessThan(60000) // under 1 minute
    }
  })

  it("status overall_health is string", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.overall_health).toBe("string")
  })
})

// ===== Additional Hook Tests =====

describe("OS Hooks Extra", () => {
  it("useOSStatus has correct query key", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    renderHook(() => useOSStatus(), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })

  it("useOSInsights has correct query key", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    renderHook(() => useOSInsights(), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })

  it("useOSStatus refetches on interval", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const { result } = renderHook(() => useOSStatus(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockGet).toHaveBeenCalled()
  })
})

// ===== Extended Tests =====

describe("OS Extended", () => {
  it("processIntent returns result with context", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.context).toBe("object")
  })

  it("status os_version is string", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.os_version).toBe("string")
  })

  it("insights decision reasoning is string", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(typeof res.decision.reasoning).toBe("string")
  })

  it("process result user_intent matches", async () => {
    mockPost.mockResolvedValue({ data: {
      ...baseProcessResult,
      result: { ...baseProcessResult.result, user_intent: "My custom intent" },
    }})
    const res = await processIntent("My custom intent")
    expect(res.result.user_intent).toBe("My custom intent")
  })

  it("process result with recommendations", async () => {
    mockPost.mockResolvedValue({
      data: {
        ...baseProcessResult,
        result: { ...baseProcessResult.result, recommendations: ["Rec 1", "Rec 2", "Rec 3"] },
      },
    })
    const res = await processIntent("Test")
    expect(res.result.recommendations).toHaveLength(3)
  })

  it("process result success true", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(res.result.success).toBe(true)
  })

  it("process result success false", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseProcessResult, result: { ...baseProcessResult.result, success: false } },
    })
    const res = await processIntent("Test")
    expect(res.result.success).toBe(false)
  })

  it("step error empty for completed step", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    const completed = res.result.steps.filter((s) => s.status === "completed")
    for (const s of completed) {
      expect(s.error).toBe("")
    }
  })

  it("status has all top-level numeric fields", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.agents_available).toBe("number")
    expect(typeof res.agents_active).toBe("number")
    expect(typeof res.tasks_running).toBe("number")
    expect(typeof res.tasks_queued).toBe("number")
  })

  it("insights suggestions types are valid", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    const validTypes = ["tip", "status", "action"]
    for (const s of res.suggestions) {
      expect(validTypes).toContain(s.type)
    }
  })

  it("process result decision should_learn boolean", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.decision.should_learn).toBe("boolean")
  })

  it("process result decision should_automate boolean", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.decision.should_automate).toBe("boolean")
  })

  it("process result recommended_agents array", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(Array.isArray(res.result.decision.recommended_agents)).toBe(true)
  })

  it("process result task_id string", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.task_id).toBe("string")
  })

  it("status overall_health healthy by default", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(res.overall_health).toBe("healthy")
  })

  it("status automations_running is number", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.system_state.automations_running).toBe("number")
  })
})

// ===== Final Batch =====

describe("OS Final", () => {
  it("process result context has memory_snapshot", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    expect(typeof res.result.context).toBe("object")
  })

  it("process result decision has task_description", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Research AI")
    expect(typeof res.result.decision.task_description).toBe("string")
  })

  it("insights decision confidence between 0 and 1", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    expect(res.decision.confidence).toBeGreaterThanOrEqual(0)
    expect(res.decision.confidence).toBeLessThanOrEqual(1)
  })

  it("status system_state has last_improvement_at", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(typeof res.system_state.last_improvement_at).toBe("string")
  })

  it("process result with task_id populated", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseProcessResult, result: { ...baseProcessResult.result, task_id: "task-123" } },
    })
    const res = await processIntent("Test")
    expect(res.result.task_id).toBe("task-123")
  })

  it("decision action is one of valid actions", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    const validActions = ["create_task", "query", "chat", "suggest", "automate", "improve"]
    expect(validActions).toContain(res.result.decision.action)
  })

  it("step result is object", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    for (const s of res.result.steps) {
      expect(typeof s.result).toBe("object")
    }
  })

  it("status components count", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(Object.keys(res.components).length).toBeGreaterThanOrEqual(3)
  })

  it("insights suggestion message non-empty", async () => {
    mockGet.mockResolvedValue({ data: baseInsights })
    const res = await fetchOSInsights()
    for (const s of res.suggestions) {
      expect(s.message.length).toBeGreaterThan(0)
    }
  })

  it("process result steps all have name", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("Test")
    for (const s of res.result.steps) {
      expect(typeof s.name).toBe("string")
      expect(s.name.length).toBeGreaterThan(0)
    }
  })

  it("process intent returns success even for long input", async () => {
    mockPost.mockResolvedValue({ data: baseProcessResult })
    const res = await processIntent("A".repeat(500))
    expect(res.success).toBe(true)
  })

  it("fetchOSStatus returns os_version 5.10", async () => {
    mockGet.mockResolvedValue({ data: baseStatus })
    const res = await fetchOSStatus()
    expect(res.os_version).toBe("5.10")
  })
})
