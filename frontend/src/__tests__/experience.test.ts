import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  searchExperience,
  submitFeedback,
  fetchExperienceStats,
  fetchRecommendations,
} from "../api/experience"
import { useExperienceStats, useRecommendations } from "../hooks/useExperience"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseStats = {
  experience: {
    total_records: 10,
    success_count: 7,
    failure_count: 3,
    success_rate: 0.7,
    top_patterns: [{ pattern: "analyze", count: 5, success_rate: 0.8 }],
    top_agents: [{ agent_id: "researcher", success_rate: 0.9, total: 8 }],
    recent_failures: [{ task_pattern: "bad task", agents: ["mock"], error: "timeout", created_at: "2026-01-01T00:00:00" }],
  },
  feedback: { total: 2, average_rating: 7.5, ratings: [{ task_id: "t1", pattern: "test", rating: 8 }] },
}

// --- API Tests ---

describe("Experience API", () => {
  it("searchExperience returns results", async () => {
    mockGet.mockResolvedValue({ data: { query: "test", results: [], total: 0 } })
    const res = await searchExperience("test")
    expect(res.query).toBe("test")
    expect(mockGet).toHaveBeenCalledWith("/experience/search", { params: { q: "test", success: undefined, limit: 20 } })
  })

  it("searchExperience with success filter", async () => {
    mockGet.mockResolvedValue({ data: { query: "test", results: [], total: 0 } })
    await searchExperience("test", true)
    expect(mockGet).toHaveBeenCalledWith("/experience/search", { params: { q: "test", success: true, limit: 20 } })
  })

  it("submitFeedback sends request", async () => {
    mockPost.mockResolvedValue({ data: { success: true, rating: 8 } })
    const res = await submitFeedback("t1", 8, "good", "test pattern")
    expect(res.success).toBe(true)
    expect(res.rating).toBe(8)
  })

  it("fetchExperienceStats returns stats", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.experience.total_records).toBe(10)
    expect(res.feedback.average_rating).toBe(7.5)
  })

  it("fetchRecommendations returns recs", async () => {
    mockGet.mockResolvedValue({
      data: { task_pattern: "test", recommended_agents: ["a1"], historical_success_rate: 0.8, similar_experiences_count: 3, warnings: [] },
    })
    const res = await fetchRecommendations("test")
    expect(res.recommended_agents).toEqual(["a1"])
    expect(mockGet).toHaveBeenCalledWith("/experience/recommendations", { params: { task_pattern: "test" } })
  })
})

// --- Response Parsing ---

describe("Experience response parsing", () => {
  it("parses stats total_records", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.experience.total_records).toBe(10)
  })

  it("parses success_rate as number", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.experience.success_rate).toBeTypeOf("number")
  })

  it("parses top_patterns array", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.experience.top_patterns).toHaveLength(1)
    expect(res.experience.top_patterns[0].pattern).toBe("analyze")
  })

  it("parses top_agents array", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.experience.top_agents[0].agent_id).toBe("researcher")
  })

  it("parses feedback ratings", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(res.feedback.total).toBe(2)
    expect(res.feedback.ratings).toHaveLength(1)
  })

  it("parses recommendations warnings", async () => {
    mockGet.mockResolvedValue({
      data: { task_pattern: "x", recommended_agents: [], historical_success_rate: 0, similar_experiences_count: 0, warnings: ["Watch out"] },
    })
    const res = await fetchRecommendations("x")
    expect(res.warnings).toEqual(["Watch out"])
  })
})

// --- Hook Tests ---

describe("useExperienceStats hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const { result } = renderHook(() => useExperienceStats(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.experience.total_records).toBe(10)
  })
})

describe("useRecommendations hook", () => {
  it("returns data for valid pattern", async () => {
    mockGet.mockResolvedValue({
      data: { task_pattern: "test", recommended_agents: ["a1"], historical_success_rate: 0.5, similar_experiences_count: 2, warnings: [] },
    })
    const { result } = renderHook(() => useRecommendations("test"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.recommended_agents).toEqual(["a1"])
  })
})

// --- Error Handling ---

describe("Experience error handling", () => {
  it("handles network error on stats", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchExperienceStats()).rejects.toThrow("Network Error")
  })

  it("handles network error on search", async () => {
    mockGet.mockRejectedValue(new Error("Timeout"))
    await expect(searchExperience("test")).rejects.toThrow("Timeout")
  })

  it("handles network error on recommendations", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    await expect(fetchRecommendations("test")).rejects.toThrow("Failed")
  })

  it("handles network error on feedback", async () => {
    mockPost.mockRejectedValue(new Error("Service Unavailable"))
    await expect(submitFeedback("t1", 5)).rejects.toThrow("Service Unavailable")
  })
})

// --- Edge Cases ---

describe("Experience edge cases", () => {
  it("handles empty stats", async () => {
    mockGet.mockResolvedValue({
      data: {
        experience: { total_records: 0, success_count: 0, failure_count: 0, success_rate: 0, top_patterns: [], top_agents: [], recent_failures: [] },
        feedback: { total: 0, average_rating: 0, ratings: [] },
      },
    })
    const res = await fetchExperienceStats()
    expect(res.experience.total_records).toBe(0)
  })

  it("handles zero success rate", async () => {
    mockGet.mockResolvedValue({
      data: {
        experience: { total_records: 5, success_count: 0, failure_count: 5, success_rate: 0, top_patterns: [], top_agents: [], recent_failures: [] },
        feedback: { total: 0, average_rating: 0, ratings: [] },
      },
    })
    const res = await fetchExperienceStats()
    expect(res.experience.success_rate).toBe(0)
  })

  it("handles perfect success rate", async () => {
    mockGet.mockResolvedValue({
      data: {
        experience: { total_records: 3, success_count: 3, failure_count: 0, success_rate: 1.0, top_patterns: [], top_agents: [], recent_failures: [] },
        feedback: { total: 0, average_rating: 0, ratings: [] },
      },
    })
    const res = await fetchExperienceStats()
    expect(res.experience.success_rate).toBe(1.0)
  })

  it("handles empty recommendations", async () => {
    mockGet.mockResolvedValue({
      data: { task_pattern: "new", recommended_agents: [], historical_success_rate: 0, similar_experiences_count: 0, warnings: [] },
    })
    const res = await fetchRecommendations("new")
    expect(res.recommended_agents).toEqual([])
  })
})

// --- Loading States ---

describe("Experience loading states", () => {
  it("shows loading initially for stats", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useExperienceStats(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("shows loading initially for recommendations", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useRecommendations("test"), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
})

// --- Search Result Fields ---

describe("Experience search result fields", () => {
  it("has task_pattern field", async () => {
    mockGet.mockResolvedValue({
      data: { query: "test", results: [{ task_pattern: "analyze", agents: [], success: true, duration_ms: 100, metadata: {}, created_at: "2026-01-01T00:00:00" }], total: 1 },
    })
    const res = await searchExperience("test")
    expect(res.results[0].task_pattern).toBe("analyze")
  })

  it("has success boolean", async () => {
    mockGet.mockResolvedValue({
      data: { query: "test", results: [{ task_pattern: "x", agents: [], success: true, duration_ms: 100, metadata: {}, created_at: "" }], total: 1 },
    })
    const res = await searchExperience("test")
    expect(res.results[0].success).toBe(true)
  })

  it("has agents array", async () => {
    mockGet.mockResolvedValue({
      data: { query: "test", results: [{ task_pattern: "x", agents: ["a", "b"], success: true, duration_ms: 100, metadata: {}, created_at: "" }], total: 1 },
    })
    const res = await searchExperience("test")
    expect(res.results[0].agents).toEqual(["a", "b"])
  })
})

// --- Feedback Edge Cases ---

describe("Feedback edge cases", () => {
  it("handles feedback without task pattern", async () => {
    mockPost.mockResolvedValue({ data: { success: true, rating: 6 } })
    const res = await submitFeedback("t1", 6, "", "")
    expect(res.success).toBe(true)
  })

  it("handles feedback with missing task id", async () => {
    mockPost.mockResolvedValue({ data: { success: false } })
    const res = await submitFeedback("", 5)
    expect(res.success).toBe(false)
  })
})

// --- Stats Field Validation ---

describe("Stats field validation", () => {
  it("recent_failures is an array", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(Array.isArray(res.experience.recent_failures)).toBe(true)
  })

  it("feedback ratings is an array", async () => {
    mockGet.mockResolvedValue({ data: baseStats })
    const res = await fetchExperienceStats()
    expect(Array.isArray(res.feedback.ratings)).toBe(true)
  })
})