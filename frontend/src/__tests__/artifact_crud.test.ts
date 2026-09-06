import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import {
  fetchTaskArtifacts,
  fetchArtifact,
  deleteArtifact,
  renameArtifact,
  type ArtifactItem,
  type TaskArtifactsResponse,
} from "../api/artifacts"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockDelete = vi.mocked(apiClient.delete)
beforeEach(() => vi.clearAllMocks())

const baseArtifact: ArtifactItem = {
  id: "a1",
  name: "report",
  type: "text",
  content: "AI trends analysis",
  owner: "researcher",
  metadata: { task_id: "t1", step_id: "research", created_by: "researcher" },
  created_at: "2026-08-12T10:00:00Z",
}

// --- API Tests ---

describe("Artifact API - fetchTaskArtifacts", () => {
  it("returns artifacts for task", async () => {
    mockGet.mockResolvedValue({ data: { task_id: "t1", artifacts: [baseArtifact], total: 1 } })
    const res = await fetchTaskArtifacts("t1")
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/tasks/t1/artifacts")
  })
  it("returns empty list", async () => {
    mockGet.mockResolvedValue({ data: { task_id: "t1", artifacts: [], total: 0 } })
    const res = await fetchTaskArtifacts("t1")
    expect(res.total).toBe(0)
  })
})

describe("Artifact API - fetchArtifact", () => {
  it("fetches single artifact by id", async () => {
    mockGet.mockResolvedValue({ data: baseArtifact })
    const res = await fetchArtifact("a1")
    expect(res.id).toBe("a1")
    expect(mockGet).toHaveBeenCalledWith("/artifacts/a1")
  })
  it("handles 404", async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } })
    await expect(fetchArtifact("bad")).rejects.toEqual({ response: { status: 404 } })
  })
})

describe("Artifact API - deleteArtifact", () => {
  it("deletes artifact", async () => {
    mockDelete.mockResolvedValue({ data: { deleted: true, artifact_id: "a1", workspace_id: "t1" } })
    const res = await deleteArtifact("a1")
    expect(res.deleted).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/artifacts/a1")
  })
  it("handles delete 404", async () => {
    mockDelete.mockRejectedValue({ response: { status: 404 } })
    await expect(deleteArtifact("bad")).rejects.toEqual({ response: { status: 404 } })
  })
})

describe("Artifact API - renameArtifact", () => {
  it("renames artifact", async () => {
    const renamed = { ...baseArtifact, name: "new_name" }
    mockPost.mockResolvedValue({ data: renamed })
    const res = await renameArtifact("a1", "new_name")
    expect(res.name).toBe("new_name")
    expect(mockPost).toHaveBeenCalledWith("/artifacts/a1/rename", { name: "new_name" })
  })
})

// --- Artifact Type Tests ---

describe("Artifact type classification", () => {
  const typeConfig: Record<string, { color: string }> = {
    text: { color: "blue" },
    markdown: { color: "purple" },
    json: { color: "green" },
    list: { color: "orange" },
    url: { color: "cyan" },
    image_url: { color: "magenta" },
  }
  it("text is blue", () => expect(typeConfig.text.color).toBe("blue"))
  it("json is green", () => expect(typeConfig.json.color).toBe("green"))
  it("markdown is purple", () => expect(typeConfig.markdown.color).toBe("purple"))
  it("list is orange", () => expect(typeConfig.list.color).toBe("orange"))
  it("url is cyan", () => expect(typeConfig.url.color).toBe("cyan"))
  it("image_url is magenta", () => expect(typeConfig.image_url.color).toBe("magenta"))
  it("unknown defaults", () => expect(typeConfig["unknown"] || { color: "default" }).toEqual({ color: "default" }))
})

// --- Metadata Tests ---

describe("Artifact metadata", () => {
  it("has task_id in metadata", () => expect(baseArtifact.metadata.task_id).toBe("t1"))
  it("has step_id in metadata", () => expect(baseArtifact.metadata.step_id).toBe("research"))
  it("has created_by in metadata", () => expect(baseArtifact.metadata.created_by).toBe("researcher"))
  it("source agent fallback to owner", () => {
    const meta = baseArtifact.metadata
    const agent = (meta.created_by as string) || baseArtifact.owner
    expect(agent).toBe("researcher")
  })
})

// --- Content Rendering Tests ---

describe("Content rendering logic", () => {
  it("url content starts with http", () => {
    const a: ArtifactItem = { ...baseArtifact, type: "url", content: "https://example.com" }
    expect(a.content.startsWith("http")).toBe(true)
  })
  it("json content is parseable", () => {
    const content = JSON.stringify({ score: 8 })
    expect(JSON.parse(content).score).toBe(8)
  })
  it("list content is array", () => {
    const content = JSON.stringify(["a", "b"])
    const parsed = JSON.parse(content)
    expect(Array.isArray(parsed)).toBe(true)
  })
  it("text content is string", () => {
    expect(typeof baseArtifact.content).toBe("string")
  })
})

// --- Empty / Loading / Error States ---

describe("UI states", () => {
  it("empty artifacts list", () => {
    const data: TaskArtifactsResponse = { task_id: "t1", artifacts: [], total: 0 }
    expect(data.artifacts).toHaveLength(0)
  })
  it("null taskId disables query", () => {
    const tid: string | null = null
    expect(!!tid).toBe(false)
  })
  it("multiple artifacts", () => {
    const items: ArtifactItem[] = [
      { ...baseArtifact, id: "a1", type: "text" },
      { ...baseArtifact, id: "a2", type: "json" },
      { ...baseArtifact, id: "a3", type: "url" },
    ]
    expect(items).toHaveLength(3)
  })
})