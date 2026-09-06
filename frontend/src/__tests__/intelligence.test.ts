import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { processCommand, fetchCommandHistory } from "../api/intelligence"
import { useCommandHistory } from "../hooks/useIntelligence"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseCommandResponse = {
  success: true,
  intent: { task_type: "research", complexity: "simple", required_agents: ["researcher"], required_tools: ["memory_search"], confidence: 0.8, metadata: {} },
  task_id: "task-1",
  classification: { task_type: "research", confidence: 0.8, keywords_matched: ["research"] },
  confidence: 0.8,
  created_at: "2026-01-01T00:00:00",
}

const baseHistory = {
  history: [{ prompt: "research AI", intent: { task_type: "research", complexity: "simple", required_agents: [], required_tools: [], confidence: 0.8, metadata: {} }, task_id: "t1", created_at: "2026-01-01T00:00:00" }],
  total: 1,
}

// --- API Tests ---

describe("Intelligence API", () => {
  it("processCommand returns result", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("research AI")
    expect(res.success).toBe(true)
    expect(res.task_id).toBe("task-1")
    expect(mockPost).toHaveBeenCalledWith("/intelligence/command", { prompt: "research AI" })
  })

  it("fetchCommandHistory returns history", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const res = await fetchCommandHistory()
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/intelligence/history")
  })
})

// --- Response Parsing ---

describe("Intelligence response parsing", () => {
  it("parses intent task_type", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.intent.task_type).toBe("research")
  })

  it("parses required_agents", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.intent.required_agents).toEqual(["researcher"])
  })

  it("parses required_tools", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.intent.required_tools).toContain("memory_search")
  })

  it("parses confidence as number", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.confidence).toBeTypeOf("number")
  })

  it("parses classification", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.classification.task_type).toBe("research")
  })

  it("parses history items", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const res = await fetchCommandHistory()
    expect(res.history).toHaveLength(1)
    expect(res.history[0].prompt).toBe("research AI")
  })
})

// --- Hook Tests ---

describe("useCommandHistory hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const { result } = renderHook(() => useCommandHistory(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
  })
})

// --- Error Handling ---

describe("Intelligence error handling", () => {
  it("handles network error on command", async () => {
    mockPost.mockRejectedValue(new Error("Network Error"))
    await expect(processCommand("test")).rejects.toThrow("Network Error")
  })

  it("handles network error on history", async () => {
    mockGet.mockRejectedValue(new Error("Timeout"))
    await expect(fetchCommandHistory()).rejects.toThrow("Timeout")
  })

  it("handles hook error state", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useCommandHistory(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// --- Edge Cases ---

describe("Intelligence edge cases", () => {
  it("handles unknown task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "unknown" } },
    })
    const res = await processCommand("xyz")
    expect(res.intent.task_type).toBe("unknown")
  })

  it("handles empty history", async () => {
    mockGet.mockResolvedValue({ data: { history: [], total: 0 } })
    const res = await fetchCommandHistory()
    expect(res.total).toBe(0)
  })

  it("handles zero confidence", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, confidence: 0, intent: { ...baseCommandResponse.intent, confidence: 0 } },
    })
    const res = await processCommand("?")
    expect(res.confidence).toBe(0)
  })
})

// --- Loading States ---

describe("Intelligence loading states", () => {
  it("shows loading for history", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useCommandHistory(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
})

// --- Intent Field Validation ---

describe("Intent field validation", () => {
  it("complexity is a string", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(res.intent.complexity).toBeTypeOf("string")
  })

  it("required_agents is an array", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(Array.isArray(res.intent.required_agents)).toBe(true)
  })

  it("required_tools is an array", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(Array.isArray(res.intent.required_tools)).toBe(true)
  })

  it("metadata is an object", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(typeof res.intent.metadata).toBe("object")
  })
})

// --- History Field Validation ---

describe("History field validation", () => {
  it("history items have prompt", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const res = await fetchCommandHistory()
    expect(res.history[0].prompt).toBeTruthy()
  })

  it("history items have task_id", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const res = await fetchCommandHistory()
    expect(res.history[0].task_id).toBeTruthy()
  })

  it("history items have created_at", async () => {
    mockGet.mockResolvedValue({ data: baseHistory })
    const res = await fetchCommandHistory()
    expect(res.history[0].created_at).toBeTruthy()
  })
})

// --- Classification Validation ---

describe("Classification validation", () => {
  it("classification has keywords_matched", async () => {
    mockPost.mockResolvedValue({ data: baseCommandResponse })
    const res = await processCommand("x")
    expect(Array.isArray(res.classification.keywords_matched)).toBe(true)
  })
})

// --- Edge Cases Extended ---

describe("Intelligence edge cases extended", () => {
  it("handles all required_tools being empty", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, required_tools: [], required_agents: [] } },
    })
    const res = await processCommand("x")
    expect(res.intent.required_tools).toEqual([])
  })

  it("handles writing task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "writing", required_agents: ["writer"] }, classification: { task_type: "writing", confidence: 0.9, keywords_matched: ["write"] } },
    })
    const res = await processCommand("write something")
    expect(res.intent.task_type).toBe("writing")
  })

  it("handles coding task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "coding", required_agents: ["mock"] }, classification: { task_type: "coding", confidence: 0.7, keywords_matched: ["code", "fix"] } },
    })
    const res = await processCommand("fix the code")
    expect(res.intent.task_type).toBe("coding")
  })
})
// --- Additional edge cases ---

describe("Additional edge cases", () => {
  it("handles analysis task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "analysis" } },
    })
    const res = await processCommand("analyze")
    expect(res.intent.task_type).toBe("analysis")
  })

  it("handles document task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "document", required_tools: ["pdf_reader"] } },
    })
    const res = await processCommand("convert pdf")
    expect(res.intent.task_type).toBe("document")
  })

  it("handles automation task type", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseCommandResponse, intent: { ...baseCommandResponse.intent, task_type: "automation" } },
    })
    const res = await processCommand("automate workflow")
    expect(res.intent.task_type).toBe("automation")
  })
})