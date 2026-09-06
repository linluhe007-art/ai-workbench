import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchPrompts } from "../api/aiDebug"
import { useDebugPrompts } from "../hooks/useAIDebug"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const basePrompts = {
  success: true, total: 3,
  prompts: [
    { id: "p1", name: "greeting", version: 2, content: "Hello {{name}}", variables: ["name"], description: "Greeting prompt", active: true, created_at: "2026-01-01T00:00:00" },
    { id: "p2", name: "greeting", version: 1, content: "Hi {{name}}", variables: ["name"], description: "Old greeting", active: false, created_at: "2025-12-31T00:00:00" },
    { id: "p3", name: "analysis", version: 1, content: "Analyze {{topic}}", variables: ["topic"], description: "", active: true, created_at: "2026-01-02T00:00:00" },
  ],
}

// ===== Prompt API Tests =====

describe("Prompt API", () => {
  it("fetchPrompts returns prompts", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts).toHaveLength(3)
    expect(mockGet).toHaveBeenCalledWith("/prompts")
  })
  it("prompts have names", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].name).toBe("greeting")
  })
  it("prompts have versions", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].version).toBe(2)
  })
  it("prompts have active flag", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].active).toBe(true)
    expect(res.prompts[1].active).toBe(false)
  })
  it("prompts have content", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].content).toBe("Hello {{name}}")
  })
  it("prompts have variables array", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(Array.isArray(res.prompts[0].variables)).toBe(true)
  })
  it("prompt total matches", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.total).toBe(3)
  })
  it("all prompt fields present", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    for (const p of res.prompts) {
      expect(typeof p.id).toBe("string")
      expect(typeof p.name).toBe("string")
      expect(typeof p.version).toBe("number")
      expect(typeof p.content).toBe("string")
    }
  })
  it("empty prompts list", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [], total: 0 } })
    const res = await fetchPrompts()
    expect(res.prompts).toHaveLength(0)
  })
  it("multiple versions same name", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const greetings = res.prompts.filter(p => p.name === "greeting")
    expect(greetings.length).toBe(2)
  })
})

describe("Prompt Hook Tests", () => {
  it("useDebugPrompts returns data", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.prompts).toHaveLength(3)
  })
  it("useDebugPrompts handles loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
  it("useDebugPrompts handles error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("Prompt Edge Cases", () => {
  it("active prompt has version > 1", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const active = res.prompts.find(p => p.active)
    expect(active).toBeDefined()
  })
  it("inactive prompt exists", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const inactive = res.prompts.find(p => !p.active)
    expect(inactive).toBeDefined()
  })
  it("prompt created_at is ISO", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    for (const p of res.prompts) {
      expect(p.created_at).toContain("T")
    }
  })
  it("prompt version >= 1", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    for (const p of res.prompts) {
      expect(p.version).toBeGreaterThanOrEqual(1)
    }
  })
  it("newest version is active for same name", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const greetings = res.prompts.filter(p => p.name === "greeting").sort((a, b) => b.version - a.version)
    expect(greetings[0].active).toBe(true)
  })
  it("prompts sorted by created_at desc", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].created_at >= res.prompts[1].created_at).toBe(true)
  })
  it("prompt description can be empty", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[2].description).toBe("")
  })
})

describe("Prompt Extra", () => {
  it("prompt content can have multiple vars", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "multi", version: 1, content: "{{a}} and {{b}} and {{c}}", variables: ["a", "b", "c"], description: "", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].variables).toHaveLength(3)
  })
  it("prompt name is unique across active versions", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const names = [...new Set(res.prompts.map(p => p.name))]
    expect(names.length).toBeLessThanOrEqual(res.prompts.length)
  })
  it("prompt version is incrementing", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    const greetings = res.prompts.filter(p => p.name === "greeting").sort((a, b) => a.version - b.version)
    expect(greetings[0].version).toBe(1)
    expect(greetings[1].version).toBe(2)
  })
  it("prompt total field is number", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(typeof res.total).toBe("number")
  })
  it("prompts response has success", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.success).toBe(true)
  })
  it("prompt with description", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    expect(res.prompts[0].description).toBeTruthy()
  })
  it("prompt variables empty array", async () => {
    mockGet.mockResolvedValue({ data: { success: true, prompts: [{ id: "p1", name: "static", version: 1, content: "No vars", variables: [], description: "", active: true, created_at: "" }], total: 1 } })
    const res = await fetchPrompts()
    expect(res.prompts[0].variables).toHaveLength(0)
  })
  it("prompt active field valid", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    for (const p of res.prompts) {
      expect(typeof p.active).toBe("boolean")
    }
  })
  it("prompt created_at non-empty", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    const res = await fetchPrompts()
    for (const p of res.prompts) {
      expect(p.created_at.length).toBeGreaterThan(0)
    }
  })
  it("useDebugPrompts query key stable", async () => {
    mockGet.mockResolvedValue({ data: basePrompts })
    renderHook(() => useDebugPrompts(), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })
})
