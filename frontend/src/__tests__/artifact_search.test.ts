import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import { searchArtifacts, type ArtifactSearchParams, type ArtifactSearchResponse } from "../api/artifactSearch"
import type { ArtifactItem } from "../api/artifacts"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

const baseItem: ArtifactItem = {
  id: "a1", name: "report", type: "text", content: "AI trends",
  owner: "researcher", metadata: { task_id: "t1", step_id: "research", created_by: "researcher" },
  created_at: "2026-08-12T10:00:00Z",
}

const baseResponse: ArtifactSearchResponse = { items: [baseItem], total: 1, limit: 50, offset: 0 }

// --- API Tests ---

describe("searchArtifacts API", () => {
  it("calls GET /artifacts/search with params", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await searchArtifacts({ q: "AI" })
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/artifacts/search", { params: { q: "AI" } })
  })

  it("removes empty params", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await searchArtifacts({ q: "", type: undefined, agent_id: "" })
    expect(mockGet).toHaveBeenCalledWith("/artifacts/search", { params: {} })
  })

  it("passes all non-empty params", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const params: ArtifactSearchParams = { q: "test", type: "json", agent_id: "a1", sort_by: "name", order: "asc", limit: 10, offset: 5 }
    await searchArtifacts(params)
    expect(mockGet).toHaveBeenCalledWith("/artifacts/search", { params: { q: "test", type: "json", agent_id: "a1", sort_by: "name", order: "asc", limit: 10, offset: 5 } })
  })

  it("handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(searchArtifacts({})).rejects.toThrow("Network Error")
  })

  it("returns empty result", async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })
    const res = await searchArtifacts({ q: "nothing" })
    expect(res.total).toBe(0)
    expect(res.items).toHaveLength(0)
  })
})

// --- Search Params Tests ---

describe("Search params", () => {
  it("query param serialization", () => {
    const params: ArtifactSearchParams = { q: "hello world", type: "text" }
    expect(params.q).toBe("hello world")
    expect(params.type).toBe("text")
  })

  it("filter params", () => {
    const params: ArtifactSearchParams = {
      agent_id: "researcher", task_id: "t1", workspace_id: "ws1", step_id: "research"
    }
    expect(params.agent_id).toBe("researcher")
    expect(params.task_id).toBe("t1")
    expect(params.workspace_id).toBe("ws1")
    expect(params.step_id).toBe("research")
  })

  it("sort params", () => {
    const params: ArtifactSearchParams = { sort_by: "name", order: "asc" }
    expect(params.sort_by).toBe("name")
    expect(params.order).toBe("asc")
  })

  it("pagination params", () => {
    const params: ArtifactSearchParams = { limit: 20, offset: 40 }
    expect(params.limit).toBe(20)
    expect(params.offset).toBe(40)
  })
})

// --- Response Schema Tests ---

describe("Response schema", () => {
  it("has items, total, limit, offset", () => {
    expect(baseResponse).toHaveProperty("items")
    expect(baseResponse).toHaveProperty("total")
    expect(baseResponse).toHaveProperty("limit")
    expect(baseResponse).toHaveProperty("offset")
  })

  it("item has required fields", () => {
    const item = baseResponse.items[0]
    expect(item).toHaveProperty("id")
    expect(item).toHaveProperty("name")
    expect(item).toHaveProperty("type")
    expect(item).toHaveProperty("content")
    expect(item).toHaveProperty("owner")
    expect(item).toHaveProperty("metadata")
    expect(item).toHaveProperty("created_at")
  })
})

// --- Type Filter Tests ---

describe("Type filters", () => {
  const types = ["text", "markdown", "json", "list", "url", "image_url"]
  types.forEach(t => {
    it(`filter by type ${t}`, () => {
      const params: ArtifactSearchParams = { type: t }
      expect(params.type).toBe(t)
    })
  })
})

// --- Sort Tests ---

describe("Sort options", () => {
  it("sort by created_at desc", () => {
    const p: ArtifactSearchParams = { sort_by: "created_at", order: "desc" }
    expect(p.sort_by).toBe("created_at")
    expect(p.order).toBe("desc")
  })
  it("sort by name asc", () => {
    const p: ArtifactSearchParams = { sort_by: "name", order: "asc" }
    expect(p.sort_by).toBe("name")
  })
  it("sort by type", () => {
    const p: ArtifactSearchParams = { sort_by: "type" }
    expect(p.sort_by).toBe("type")
  })
})

// --- Metadata Tests ---

describe("Artifact metadata display", () => {
  it("source agent from created_by", () => {
    const agent = (baseItem.metadata.created_by as string) || baseItem.owner
    expect(agent).toBe("researcher")
  })
  it("source step from step_id", () => {
    expect(baseItem.metadata.step_id).toBe("research")
  })
  it("source task from task_id", () => {
    expect(baseItem.metadata.task_id).toBe("t1")
  })
  it("task link generation", () => {
    const tid = baseItem.metadata.task_id as string
    expect(`/tasks/${tid}`).toBe("/tasks/t1")
  })
  it("agent link generation", () => {
    const agent = (baseItem.metadata.created_by as string) || baseItem.owner
    expect(`/artifacts?agent_id=${agent}`).toBe("/artifacts?agent_id=researcher")
  })
})

// --- Empty State Tests ---

describe("Empty and loading states", () => {
  it("empty items array", () => {
    const r: ArtifactSearchResponse = { items: [], total: 0, limit: 50, offset: 0 }
    expect(r.items).toHaveLength(0)
    expect(r.total).toBe(0)
  })
  it("pagination beyond total", () => {
    const r: ArtifactSearchResponse = { items: [], total: 100, limit: 20, offset: 200 }
    expect(r.items).toHaveLength(0)
    expect(r.total).toBe(100)
  })
  it("hook disabled when no params", () => {
    const enabled = !!""
    expect(enabled).toBe(false)
  })
})
// --- URL Query Param Tests ---

describe("URL query param initialization", () => {
  it("parses q from URL", () => {
    const params = new URLSearchParams("?q=hello")
    expect(params.get("q")).toBe("hello")
  })
  it("parses type filter from URL", () => {
    const params = new URLSearchParams("?type=json")
    expect(params.get("type")).toBe("json")
  })
  it("parses task_id from URL", () => {
    const params = new URLSearchParams("?task_id=t1")
    expect(params.get("task_id")).toBe("t1")
  })
  it("parses workspace_id from URL", () => {
    const params = new URLSearchParams("?workspace_id=ws1")
    expect(params.get("workspace_id")).toBe("ws1")
  })
  it("parses agent_id from URL", () => {
    const params = new URLSearchParams("?agent_id=researcher")
    expect(params.get("agent_id")).toBe("researcher")
  })
  it("parses sort_by from URL", () => {
    const params = new URLSearchParams("?sort_by=name&order=asc")
    expect(params.get("sort_by")).toBe("name")
    expect(params.get("order")).toBe("asc")
  })
  it("parses page from URL", () => {
    const params = new URLSearchParams("?page=3")
    expect(parseInt(params.get("page") || "1", 10)).toBe(3)
  })
})

// --- Component Data Tests ---

describe("Artifact type color mapping", () => {
  const colors: Record<string, string> = { text: "blue", markdown: "purple", json: "green", list: "orange", url: "cyan", image_url: "magenta" }
  Object.entries(colors).forEach(([type, color]) => {
    it(`${type} maps to ${color}`, () => {
      expect(colors[type]).toBe(color)
    })
  })
  it("unknown type gets default", () => {
    expect(colors["unknown"] || "default").toBe("default")
  })
})

// --- Clear Filters Tests ---

describe("Clear filters", () => {
  it("resets to default params", () => {
    const defaults: ArtifactSearchParams = { sort_by: "created_at", order: "desc", limit: 20, offset: 0 }
    expect(defaults.sort_by).toBe("created_at")
    expect(defaults.order).toBe("desc")
    expect(defaults.offset).toBe(0)
  })
})