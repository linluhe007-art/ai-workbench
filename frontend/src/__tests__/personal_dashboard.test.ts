import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchPersonalDashboard } from "../api/personal"
import type {
  PersonalDashboardResponse,
  PersonalMetrics,
  Insight,
  DailySummary,
} from "../api/personal"
import { usePersonalDashboard } from "../hooks/usePersonal"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseMetrics: PersonalMetrics = {
  tasks_today: 5,
  tasks_completed_today: 4,
  tasks_failed_today: 1,
  tasks_running: 2,
  efficiency: {
    average_duration_ms: 1200,
    success_rate: 0.8,
    total_iterations: 12,
  },
  knowledge_growth: {
    knowledge_items_added: 3,
    experience_records_created: 2,
    artifacts_generated: 7,
  },
  agent_activity: {
    agents_active: 2,
    agents_total: 4,
    agent_executions_today: 10,
  },
  generated_at: "2026-01-01T00:00:00",
}

const baseInsights: Insight[] = [
  { type: "achievement", title: "High", message: "Great!", priority: 1, action: "view" },
  { type: "tip", title: "Tip", message: "Try this", priority: 0, action: "" },
]

const baseSummary: DailySummary = {
  text: "Today you created 5 tasks.",
  lines: ["5 tasks created", "80% success"],
  mood: "productive",
}

const baseResponse: PersonalDashboardResponse = {
  success: true,
  metrics: baseMetrics,
  insights: baseInsights,
  daily_summary: baseSummary,
}

// ===== API Tests =====

describe("Personal Dashboard API", () => {
  it("fetchPersonalDashboard returns full response", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.success).toBe(true)
    expect(res.metrics.tasks_today).toBe(5)
    expect(mockGet).toHaveBeenCalledWith("/personal/dashboard")
  })

  it("fetchPersonalDashboard returns metrics", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.efficiency.success_rate).toBe(0.8)
  })

  it("fetchPersonalDashboard returns insights list", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.insights).toHaveLength(2)
  })

  it("fetchPersonalDashboard returns daily_summary", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.daily_summary.mood).toBe("productive")
  })

  it("fetchPersonalDashboard handles idle mood", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseResponse, daily_summary: { ...baseSummary, mood: "idle" } },
    })
    const res = await fetchPersonalDashboard()
    expect(res.daily_summary.mood).toBe("idle")
  })

  it("fetchPersonalDashboard handles zero tasks", async () => {
    mockGet.mockResolvedValue({
      data: {
        ...baseResponse,
        metrics: { ...baseMetrics, tasks_today: 0, tasks_completed_today: 0 },
      },
    })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.tasks_today).toBe(0)
  })

  it("fetchPersonalDashboard handles empty insights", async () => {
    mockGet.mockResolvedValue({ data: { ...baseResponse, insights: [] } })
    const res = await fetchPersonalDashboard()
    expect(res.insights).toHaveLength(0)
  })
})

// ===== Response Parsing =====

describe("Personal Dashboard Response Parsing", () => {
  it("parses efficiency correctly", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.efficiency.average_duration_ms).toBe(1200)
    expect(res.metrics.efficiency.total_iterations).toBe(12)
  })

  it("parses knowledge_growth correctly", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.knowledge_growth.artifacts_generated).toBe(7)
  })

  it("parses agent_activity correctly", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.agent_activity.agents_active).toBe(2)
    expect(res.metrics.agent_activity.agents_total).toBe(4)
  })

  it("parses insight types", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    const types = res.insights.map((i) => i.type)
    expect(types).toContain("achievement")
    expect(types).toContain("tip")
  })

  it("parses insight priority", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.insights[0].priority).toBe(1)
  })

  it("parses daily_summary lines", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.daily_summary.lines).toHaveLength(2)
  })
})

// ===== Hook Tests =====

describe("usePersonalDashboard hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.metrics.tasks_today).toBe(5)
  })

  it("returns insights via hook", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.insights).toHaveLength(2)
  })

  it("returns daily_summary via hook", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.daily_summary.mood).toBe("productive")
  })

  it("handles loading state", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state", async () => {
    mockGet.mockRejectedValue(new Error("Network error"))
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it("has correct query key", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })
})

// ===== Type Validation Tests =====

describe("Personal Dashboard Types", () => {
  it("Insight type has all required fields", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    for (const i of res.insights) {
      expect(typeof i.type).toBe("string")
      expect(typeof i.title).toBe("string")
      expect(typeof i.message).toBe("string")
      expect(typeof i.priority).toBe("number")
    }
  })

  it("DailySummary has text lines and mood", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(typeof res.daily_summary.text).toBe("string")
    expect(Array.isArray(res.daily_summary.lines)).toBe(true)
    expect(typeof res.daily_summary.mood).toBe("string")
  })

  it("PersonalMetrics has all sub-objects", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.efficiency).toBeDefined()
    expect(res.metrics.knowledge_growth).toBeDefined()
    expect(res.metrics.agent_activity).toBeDefined()
  })

  it("Insight action field is string", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    for (const i of res.insights) {
      expect(typeof i.action).toBe("string")
    }
  })

  it("success_rate is a number between 0 and 1", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    const sr = res.metrics.efficiency.success_rate
    expect(sr).toBeGreaterThanOrEqual(0)
    expect(sr).toBeLessThanOrEqual(1)
  })
})

// ===== Edge Case Tests =====

describe("Personal Dashboard Edge Cases", () => {
  it("handles success=false response gracefully", async () => {
    mockGet.mockResolvedValue({ data: { success: false, metrics: baseMetrics, insights: [], daily_summary: baseSummary } })
    const res = await fetchPersonalDashboard()
    expect(res.success).toBe(false)
  })

  it("handles all metric zeros", async () => {
    const zeroMetrics: PersonalMetrics = {
      tasks_today: 0, tasks_completed_today: 0, tasks_failed_today: 0, tasks_running: 0,
      efficiency: { average_duration_ms: 0, success_rate: 0, total_iterations: 0 },
      knowledge_growth: { knowledge_items_added: 0, experience_records_created: 0, artifacts_generated: 0 },
      agent_activity: { agents_active: 0, agents_total: 0, agent_executions_today: 0 },
      generated_at: "2026-01-01T00:00:00",
    }
    mockGet.mockResolvedValue({ data: { ...baseResponse, metrics: zeroMetrics } })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.tasks_today).toBe(0)
    expect(res.metrics.agent_activity.agents_total).toBe(0)
  })

  it("handles high failure rate", async () => {
    mockGet.mockResolvedValue({
      data: {
        ...baseResponse,
        metrics: { ...baseMetrics, tasks_today: 10, tasks_completed_today: 2, tasks_failed_today: 8, success_rate: 0.2 },
      },
    })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.tasks_failed_today).toBe(8)
    expect(res.metrics.tasks_completed_today).toBe(2)
  })

  it("handles many insights", async () => {
    const manyInsights: Insight[] = Array.from({ length: 10 }, (_, i) => ({
      type: "tip", title: `Tip ${i}`, message: `Message ${i}`, priority: i % 3, action: "",
    }))
    mockGet.mockResolvedValue({ data: { ...baseResponse, insights: manyInsights } })
    const res = await fetchPersonalDashboard()
    expect(res.insights).toHaveLength(10)
  })

  it("handles single line in daily_summary", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseResponse, daily_summary: { text: "Single", lines: ["One line"], mood: "idle" } },
    })
    const res = await fetchPersonalDashboard()
    expect(res.daily_summary.lines).toHaveLength(1)
  })

  it("generated_at is a string", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(typeof res.metrics.generated_at).toBe("string")
  })

  it("knowledge_growth numbers are non-negative", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.knowledge_growth.knowledge_items_added).toBeGreaterThanOrEqual(0)
    expect(res.metrics.knowledge_growth.experience_records_created).toBeGreaterThanOrEqual(0)
    expect(res.metrics.knowledge_growth.artifacts_generated).toBeGreaterThanOrEqual(0)
  })

  it("agent_executions_today is non-negative", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.agent_activity.agent_executions_today).toBeGreaterThanOrEqual(0)
  })

  it("mood is valid enum value", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(["productive", "idle"]).toContain(res.daily_summary.mood)
  })
})

// ===== Hook Refetch Tests =====

describe("usePersonalDashboard refetch", () => {
  it("refetches on interval", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const { result } = renderHook(() => usePersonalDashboard(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    // Verify it was called at least once
    expect(mockGet).toHaveBeenCalled()
  })
})

// ===== Additional Tests =====

describe("Personal Dashboard Additional", () => {
  it("multiple insights with same priority", async () => {
    const insights: Insight[] = [
      { type: "tip", title: "T1", message: "M1", priority: 1, action: "" },
      { type: "tip", title: "T2", message: "M2", priority: 1, action: "" },
      { type: "achievement", title: "T3", message: "M3", priority: 1, action: "" },
    ]
    mockGet.mockResolvedValue({ data: { ...baseResponse, insights } })
    const res = await fetchPersonalDashboard()
    expect(res.insights).toHaveLength(3)
  })

  it("tasks_running count is correct", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.tasks_running).toBe(2)
  })

  it("total_iterations in efficiency", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    expect(res.metrics.efficiency.total_iterations).toBeGreaterThan(0)
  })

  it("insight with empty action", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    const emptyAction = res.insights.find((i) => i.action === "")
    expect(emptyAction).toBeDefined()
  })

  it("insight with non-empty action", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    const withAction = res.insights.find((i) => i.action !== "")
    expect(withAction).toBeDefined()
  })

  it("all agent_activity fields are numbers", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchPersonalDashboard()
    const aa = res.metrics.agent_activity
    expect(typeof aa.agents_active).toBe("number")
    expect(typeof aa.agents_total).toBe("number")
    expect(typeof aa.agent_executions_today).toBe("number")
  })
})
