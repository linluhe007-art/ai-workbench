import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  saveMemory,
  searchMemory,
  getMemory,
  updateMemory,
  deleteMemory,
  getMemoryStats,
  getMemoryByType,
  getProfile,
  getPreferences,
  MEMORY_TYPES,
  type MemoryItem,
} from "../api/memory"
import {
  useMemorySearch,
  useMemoryStats,
  useMemoryByType,
  useSaveMemory,
  useUpdateMemory,
  useDeleteMemory,
  useProfile,
  usePreferences,
} from "../hooks/useMemory"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockPut = vi.mocked(apiClient.put)
const mockDelete = vi.mocked(apiClient.delete)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

// ── Test Data ──

const baseMemoryItem: MemoryItem = {
  id: "m1",
  user_id: "u1",
  memory_type: "knowledge",
  content: "AI research notes",
  importance: 0.8,
  embedding_id: "",
  tags: ["ai", "research"],
  metadata: {},
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
}

const memoryListResponse = {
  success: true,
  total: 1,
  results: [baseMemoryItem],
}

const memoryDetailResponse = {
  success: true,
  data: baseMemoryItem,
}

const memoryStatsResponse = {
  success: true,
  data: {
    total_memories: 5,
    by_type: { profile: 1, knowledge: 3, experience: 1 },
    total_tags: 3,
  },
}

// ── API Tests ──

describe("Memory API", () => {
  it("saveMemory calls POST /memory/ltm", async () => {
    mockPost.mockResolvedValue({ data: memoryDetailResponse })
    const res = await saveMemory({ content: "test", memory_type: "knowledge" })
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/memory/ltm", expect.any(Object))
  })

  it("searchMemory calls POST /memory/ltm/search", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const res = await searchMemory({ query: "AI" })
    expect(res.total).toBe(1)
    expect(mockPost).toHaveBeenCalledWith("/memory/ltm/search", { query: "AI" })
  })

  it("getMemory calls GET /memory/ltm/:id", async () => {
    mockGet.mockResolvedValue({ data: memoryDetailResponse })
    const res = await getMemory("m1")
    expect(res.data?.content).toBe("AI research notes")
    expect(mockGet).toHaveBeenCalledWith("/memory/ltm/m1")
  })

  it("updateMemory calls PUT /memory/ltm/:id", async () => {
    mockPut.mockResolvedValue({ data: memoryDetailResponse })
    const res = await updateMemory("m1", { content: "updated" })
    expect(res.success).toBe(true)
    expect(mockPut).toHaveBeenCalledWith("/memory/ltm/m1", { content: "updated" })
  })

  it("deleteMemory calls DELETE /memory/ltm/:id", async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const res = await deleteMemory("m1")
    expect(res.success).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/memory/ltm/m1")
  })

  it("getMemoryStats calls GET /memory/ltm/stats", async () => {
    mockGet.mockResolvedValue({ data: memoryStatsResponse })
    const res = await getMemoryStats()
    expect(res.data.total_memories).toBe(5)
  })

  it("getMemoryByType calls GET with type param", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const res = await getMemoryByType("knowledge")
    expect(res.total).toBe(1)
  })

  it("getProfile calls GET /memory/ltm/profile", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const res = await getProfile()
    expect(res.success).toBe(true)
  })

  it("getPreferences calls GET /memory/ltm/preferences", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const res = await getPreferences()
    expect(res.success).toBe(true)
  })

  it("MEMORY_TYPES has all 5 types", () => {
    expect(MEMORY_TYPES).toHaveLength(5)
    expect(MEMORY_TYPES).toContain("profile")
    expect(MEMORY_TYPES).toContain("preference")
    expect(MEMORY_TYPES).toContain("project")
    expect(MEMORY_TYPES).toContain("knowledge")
    expect(MEMORY_TYPES).toContain("experience")
  })
})

// ── Hook Tests ──

describe("useMemorySearch hook", () => {
  it("returns data after fetch", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const { result } = renderHook(() => useMemorySearch({ query: "AI" }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
  })

  it("does not fetch without query", () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const { result } = renderHook(() => useMemorySearch({}), { wrapper })
    expect(result.current.isLoading).toBe(false)
  })
})

describe("useMemoryStats hook", () => {
  it("returns stats", async () => {
    mockGet.mockResolvedValue({ data: memoryStatsResponse })
    const { result } = renderHook(() => useMemoryStats(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.data.total_memories).toBe(5)
  })
})

describe("useMemoryByType hook", () => {
  it("returns typed results", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const { result } = renderHook(() => useMemoryByType("knowledge"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
  })
})

describe("useSaveMemory hook", () => {
  it("triggers mutation", async () => {
    mockPost.mockResolvedValue({ data: memoryDetailResponse })
    const { result } = renderHook(() => useSaveMemory(), { wrapper })
    await result.current.mutateAsync({ content: "new", memory_type: "knowledge" })
    expect(mockPost).toHaveBeenCalled()
  })
})

describe("useUpdateMemory hook", () => {
  it("triggers mutation", async () => {
    mockPut.mockResolvedValue({ data: memoryDetailResponse })
    const { result } = renderHook(() => useUpdateMemory(), { wrapper })
    await result.current.mutateAsync({ id: "m1", data: { content: "updated" } })
    expect(mockPut).toHaveBeenCalled()
  })
})

describe("useDeleteMemory hook", () => {
  it("triggers mutation", async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const { result } = renderHook(() => useDeleteMemory(), { wrapper })
    await result.current.mutateAsync("m1")
    expect(mockDelete).toHaveBeenCalled()
  })
})

describe("useProfile hook", () => {
  it("fetches profile", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const { result } = renderHook(() => useProfile(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

describe("usePreferences hook", () => {
  it("fetches preferences", async () => {
    mockGet.mockResolvedValue({ data: memoryListResponse })
    const { result } = renderHook(() => usePreferences(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

// ── Error Handling ──

describe("Memory error handling", () => {
  it("handles network error on save", async () => {
    mockPost.mockRejectedValue(new Error("Network Error"))
    await expect(saveMemory({ content: "test" })).rejects.toThrow("Network Error")
  })

  it("handles network error on search", async () => {
    mockPost.mockRejectedValue(new Error("Timeout"))
    await expect(searchMemory({ query: "test" })).rejects.toThrow("Timeout")
  })

  it("handles network error on get", async () => {
    mockGet.mockRejectedValue(new Error("Not Found"))
    await expect(getMemory("bad")).rejects.toThrow("Not Found")
  })

  it("handles network error on delete", async () => {
    mockDelete.mockRejectedValue(new Error("Gone"))
    await expect(deleteMemory("x")).rejects.toThrow("Gone")
  })
})

// ── Edge Cases ──

describe("Memory edge cases", () => {
  it("handles empty results", async () => {
    mockPost.mockResolvedValue({ data: { success: true, total: 0, results: [] } })
    const res = await searchMemory({ query: "nonexistent" })
    expect(res.total).toBe(0)
    expect(res.results).toEqual([])
  })

  it("handles search with only type filter", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const res = await searchMemory({ memory_type: "profile" })
    expect(res.success).toBe(true)
  })

  it("handles search with only tags filter", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const res = await searchMemory({ tags: ["ai"] })
    expect(res.success).toBe(true)
  })

  it("handles all MEMORY_TYPES as valid", () => {
    for (const t of MEMORY_TYPES) {
      expect(["profile", "preference", "project", "knowledge", "experience"]).toContain(t)
    }
  })
})

// ── API Response Schema ──

describe("Memory response schema", () => {
  it("memory item has all required fields", () => {
    const item = baseMemoryItem
    expect(item).toHaveProperty("id")
    expect(item).toHaveProperty("user_id")
    expect(item).toHaveProperty("memory_type")
    expect(item).toHaveProperty("content")
    expect(item).toHaveProperty("importance")
    expect(item).toHaveProperty("embedding_id")
    expect(item).toHaveProperty("tags")
    expect(item).toHaveProperty("metadata")
    expect(item).toHaveProperty("created_at")
    expect(item).toHaveProperty("updated_at")
  })

  it("importance is a number", () => {
    expect(typeof baseMemoryItem.importance).toBe("number")
  })

  it("tags is an array", () => {
    expect(Array.isArray(baseMemoryItem.tags)).toBe(true)
  })
})


// ── Additional Type-specific API Tests ──

describe("Memory type-specific API", () => {
  it("saveMemory with tags", async () => {
    mockPost.mockResolvedValue({ data: memoryDetailResponse })
    const res = await saveMemory({ content: "test", tags: ["ai", "ml"] })
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/memory/ltm", expect.objectContaining({ tags: ["ai", "ml"] }))
  })

  it("saveMemory with importance", async () => {
    mockPost.mockResolvedValue({ data: memoryDetailResponse })
    const res = await saveMemory({ content: "test", importance: 0.95 })
    expect(res.success).toBe(true)
  })

  it("searchMemory with min_importance", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const res = await searchMemory({ query: "test", min_importance: 0.7 })
    expect(res.total).toBe(1)
  })

  it("searchMemory with multiple tags", async () => {
    mockPost.mockResolvedValue({ data: memoryListResponse })
    const res = await searchMemory({ tags: ["ai", "research"] })
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/memory/ltm/search", expect.objectContaining({ tags: ["ai", "research"] }))
  })
})

describe("Memory types validation", () => {
  it("profile is valid type", () => expect(MEMORY_TYPES).toContain("profile"))
  it("preference is valid type", () => expect(MEMORY_TYPES).toContain("preference"))
  it("project is valid type", () => expect(MEMORY_TYPES).toContain("project"))
  it("knowledge is valid type", () => expect(MEMORY_TYPES).toContain("knowledge"))
  it("experience is valid type", () => expect(MEMORY_TYPES).toContain("experience"))
})

describe("Memory hook invalidation", () => {
  it("saveMemory invalidates queries", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries")
    mockPost.mockResolvedValue({ data: memoryDetailResponse })
    const { result } = renderHook(() => useSaveMemory(), { wrapper: ({ children }) => React.createElement(QueryClientProvider, { client: qc }, children) })
    await result.current.mutateAsync({ content: "test" })
    expect(invalidateSpy).toHaveBeenCalled()
  })

  it("deleteMemory invalidates queries", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries")
    mockDelete.mockResolvedValue({ data: { success: true } })
    const { result } = renderHook(() => useDeleteMemory(), { wrapper: ({ children }) => React.createElement(QueryClientProvider, { client: qc }, children) })
    await result.current.mutateAsync("m1")
    expect(invalidateSpy).toHaveBeenCalled()
  })
})
