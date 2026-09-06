import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  fetchImprovementReport,
  applyImprovement,
  fetchImprovementHistory,
  revertImprovement,
} from "../api/improvement"
import type {
  ImprovementReportResponse,
  AnalysisData,
  StrategyRecommendation,
  OptimizationRecord,
} from "../api/improvement"
import {
  useImprovementReport,
  useImprovementHistory,
} from "../hooks/useImprovement"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseAnalysis: AnalysisData = {
  generated_at: "2026-01-01T00:00:00",
  task_analysis: { total_tasks: 10, completed_tasks: 8, failed_tasks: 2, success_rate: 0.8, average_duration_ms: 5000 },
  agent_performance: [
    { agent_id: "a1", executions: 10, errors: 1, success_rate: 0.9 },
    { agent_id: "a2", executions: 10, errors: 3, success_rate: 0.7 },
  ],
  best_agent: "a1",
  worst_agent: "a2",
  workflow_stats: { agents_analyzed: 2 },
  bottlenecks: [{ type: "slow_execution", severity: "medium", detail: "Slow", suggestion: "Optimize" }],
}

const baseRecs: StrategyRecommendation[] = [
  {
    id: "r1", category: "agent_selection", title: "Prefer a1",
    description: "a1 is better", priority: 2, expected_impact: "Better", action: {},
  },
  {
    id: "r2", category: "retry", title: "Retry more",
    description: "Increase retries", priority: 1, expected_impact: "More success", action: {},
  },
]

const baseReport: ImprovementReportResponse = {
  success: true,
  analysis: baseAnalysis,
  strategy_plan: {
    generated_at: "2026-01-01T00:00:00",
    recommendations: baseRecs,
    summary: "2 recommendations",
  },
}

// ===== API Tests =====

describe("Improvement API", () => {
  it("fetchImprovementReport returns report", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.success).toBe(true)
    expect(res.analysis.task_analysis.total_tasks).toBe(10)
    expect(mockGet).toHaveBeenCalledWith("/improvement/report")
  })

  it("fetchImprovementReport has strategy_plan", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.strategy_plan.recommendations).toHaveLength(2)
  })

  it("applyImprovement sends request", async () => {
    const rec: OptimizationRecord = {
      id: "o1", recommendation_id: "r1", category: "agent_selection",
      title: "Test", action: {}, status: "applied", applied_at: "2026-01-01T00:00:00", result: {},
    }
    mockPost.mockResolvedValue({ data: { success: true, applied: 1, records: [rec] } })
    const res = await applyImprovement(["r1"])
    expect(res.success).toBe(true)
    expect(res.applied).toBe(1)
    expect(mockPost).toHaveBeenCalledWith("/improvement/apply", { recommendation_ids: ["r1"] })
  })

  it("applyImprovement defaults to empty array", async () => {
    mockPost.mockResolvedValue({ data: { success: true, applied: 0, records: [] } })
    await applyImprovement()
    expect(mockPost).toHaveBeenCalledWith("/improvement/apply", { recommendation_ids: [] })
  })

  it("fetchImprovementHistory returns history", async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        records: [{ id: "o1", recommendation_id: "r1", category: "retry", title: "T", action: {}, status: "applied", applied_at: "", result: {} }],
        stats: { total_applied: 1, by_category: { retry: 1 } },
      },
    })
    const res = await fetchImprovementHistory()
    expect(res.success).toBe(true)
    expect(res.stats.total_applied).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/improvement/history")
  })

  it("revertImprovement calls correct endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true, record_id: "o1", message: "Reverted" } })
    const res = await revertImprovement("o1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/improvement/revert/o1")
  })
})

// ===== Response Parsing =====

describe("Improvement Response Parsing", () => {
  it("parses task_analysis correctly", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.task_analysis.success_rate).toBe(0.8)
  })

  it("parses agent_performance correctly", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.agent_performance[0].agent_id).toBe("a1")
    expect(res.analysis.agent_performance[0].success_rate).toBe(0.9)
  })

  it("parses bottlenecks correctly", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.bottlenecks[0].type).toBe("slow_execution")
  })

  it("parses best/worst agent", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.best_agent).toBe("a1")
    expect(res.analysis.worst_agent).toBe("a2")
  })

  it("parses recommendations categories", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    const cats = res.strategy_plan.recommendations.map((r) => r.category)
    expect(cats).toContain("agent_selection")
    expect(cats).toContain("retry")
  })
})

// ===== Hook Tests =====

describe("useImprovementReport hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const { result } = renderHook(() => useImprovementReport(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.analysis.task_analysis.total_tasks).toBe(10)
  })

  it("handles loading state", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useImprovementReport(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useImprovementReport(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it("has correct query key", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    renderHook(() => useImprovementReport(), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })
})

describe("useImprovementHistory hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({
      data: { success: true, records: [], stats: { total_applied: 0, by_category: {} } },
    })
    const { result } = renderHook(() => useImprovementHistory(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })

  it("handles error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useImprovementHistory(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ===== Type Validation =====

describe("Improvement Types", () => {
  it("AnalysisData has required fields", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(typeof res.analysis.generated_at).toBe("string")
    expect(typeof res.analysis.best_agent).toBe("string")
    expect(Array.isArray(res.analysis.agent_performance)).toBe(true)
    expect(Array.isArray(res.analysis.bottlenecks)).toBe(true)
  })

  it("StrategyRecommendation has required fields", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const r of res.strategy_plan.recommendations) {
      expect(typeof r.id).toBe("string")
      expect(typeof r.category).toBe("string")
      expect(typeof r.title).toBe("string")
      expect(typeof r.priority).toBe("number")
    }
  })

  it("OptimizationRecord has required fields", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, applied: 1, records: [{ id: "o1", recommendation_id: "r1", category: "r", title: "T", action: {}, status: "applied", applied_at: "", result: {} }] },
    })
    const res = await applyImprovement()
    expect(res.records[0].id).toBe("o1")
    expect(typeof res.records[0].status).toBe("string")
  })

  it("History stats has by_category", async () => {
    mockGet.mockResolvedValue({
      data: { success: true, records: [], stats: { total_applied: 5, by_category: { retry: 3, workflow: 2 } } },
    })
    const res = await fetchImprovementHistory()
    expect(res.stats.by_category.retry).toBe(3)
  })

  it("success_rate is between 0 and 1", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.task_analysis.success_rate).toBeGreaterThanOrEqual(0)
    expect(res.analysis.task_analysis.success_rate).toBeLessThanOrEqual(1)
  })

  it("agent_performance entries have correct types", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const ap of res.analysis.agent_performance) {
      expect(typeof ap.agent_id).toBe("string")
      expect(typeof ap.executions).toBe("number")
      expect(typeof ap.errors).toBe("number")
    }
  })

  it("bottleneck severity is valid", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const b of res.analysis.bottlenecks) {
      expect(["low", "medium", "high"]).toContain(b.severity)
    }
  })
})

// ===== Edge Cases =====

describe("Improvement Edge Cases", () => {
  it("handles empty agent_performance", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseReport, analysis: { ...baseAnalysis, agent_performance: [], best_agent: "", worst_agent: "" } },
    })
    const res = await fetchImprovementReport()
    expect(res.analysis.agent_performance).toHaveLength(0)
  })

  it("handles empty bottlenecks", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseReport, analysis: { ...baseAnalysis, bottlenecks: [] } },
    })
    const res = await fetchImprovementReport()
    expect(res.analysis.bottlenecks).toHaveLength(0)
  })

  it("handles empty recommendations", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseReport, strategy_plan: { ...baseReport.strategy_plan, recommendations: [], summary: "None" } },
    })
    const res = await fetchImprovementReport()
    expect(res.strategy_plan.recommendations).toHaveLength(0)
  })

  it("handles zero tasks", async () => {
    mockGet.mockResolvedValue({
      data: {
        ...baseReport,
        analysis: {
          ...baseAnalysis,
          task_analysis: { total_tasks: 0, completed_tasks: 0, failed_tasks: 0, success_rate: 0, average_duration_ms: 0 },
        },
      },
    })
    const res = await fetchImprovementReport()
    expect(res.analysis.task_analysis.total_tasks).toBe(0)
  })

  it("handles high failure rate", async () => {
    mockGet.mockResolvedValue({
      data: {
        ...baseReport,
        analysis: {
          ...baseAnalysis,
          task_analysis: { total_tasks: 50, completed_tasks: 10, failed_tasks: 40, success_rate: 0.2, average_duration_ms: 5000 },
        },
      },
    })
    const res = await fetchImprovementReport()
    expect(res.analysis.task_analysis.failed_tasks).toBe(40)
    expect(res.analysis.task_analysis.success_rate).toBe(0.2)
  })

  it("recommendation priority is 0, 1, or 2", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const r of res.strategy_plan.recommendations) {
      expect([0, 1, 2]).toContain(r.priority)
    }
  })

  it("apply response has records array", async () => {
    mockPost.mockResolvedValue({ data: { success: true, applied: 2, records: [] } })
    const res = await applyImprovement()
    expect(Array.isArray(res.records)).toBe(true)
  })

  it("revert nonexistent returns success false", async () => {
    mockPost.mockResolvedValue({ data: { success: false, record_id: "x", message: "Not found" } })
    const res = await revertImprovement("x")
    expect(res.success).toBe(false)
  })
})

// ===== Additional Tests =====

describe("Improvement Additional", () => {
  it("analysis generated_at is ISO format", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.analysis.generated_at).toContain("T")
  })

  it("strategy_plan generated_at is ISO format", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(res.strategy_plan.generated_at).toContain("T")
  })

  it("strategy_plan summary is a string", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(typeof res.strategy_plan.summary).toBe("string")
    expect(res.strategy_plan.summary.length).toBeGreaterThan(0)
  })

  it("recommendation has expected_impact", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const rec of res.strategy_plan.recommendations) {
      expect(typeof rec.expected_impact).toBe("string")
    }
  })

  it("recommendation has action object", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    for (const rec of res.strategy_plan.recommendations) {
      expect(typeof rec.action).toBe("object")
    }
  })

  it("history stats total_applied is number", async () => {
    mockGet.mockResolvedValue({
      data: { success: true, records: [], stats: { total_applied: 3, by_category: {} } },
    })
    const res = await fetchImprovementHistory()
    expect(typeof res.stats.total_applied).toBe("number")
  })

  it("analysis workflow_stats is an object", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(typeof res.analysis.workflow_stats).toBe("object")
  })

  it("task_analysis average_duration_ms is number", async () => {
    mockGet.mockResolvedValue({ data: baseReport })
    const res = await fetchImprovementReport()
    expect(typeof res.analysis.task_analysis.average_duration_ms).toBe("number")
    expect(res.analysis.task_analysis.average_duration_ms).toBeGreaterThanOrEqual(0)
  })
})
