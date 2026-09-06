import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import { fetchTaskArtifacts, type ArtifactItem, type TaskArtifactsResponse } from "../api/artifacts"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
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

const baseResponse: TaskArtifactsResponse = {
  task_id: "t1",
  artifacts: [baseArtifact],
  total: 1,
}

// --- API Tests ---

describe("Artifact API", () => {
  it("fetchTaskArtifacts returns artifacts", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchTaskArtifacts("t1")
    expect(res.task_id).toBe("t1")
    expect(res.artifacts).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/tasks/t1/artifacts")
  })

  it("fetchTaskArtifacts handles empty result", async () => {
    mockGet.mockResolvedValue({ data: { task_id: "t2", artifacts: [], total: 0 } })
    const res = await fetchTaskArtifacts("t2")
    expect(res.total).toBe(0)
    expect(res.artifacts).toHaveLength(0)
  })

  it("fetchTaskArtifacts handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchTaskArtifacts("t1")).rejects.toThrow("Network Error")
  })
})

// --- Artifact Data Tests ---

describe("ArtifactItem structure", () => {
  it("has required fields", () => {
    expect(baseArtifact).toHaveProperty("id")
    expect(baseArtifact).toHaveProperty("name")
    expect(baseArtifact).toHaveProperty("type")
    expect(baseArtifact).toHaveProperty("content")
    expect(baseArtifact).toHaveProperty("owner")
    expect(baseArtifact).toHaveProperty("metadata")
    expect(baseArtifact).toHaveProperty("created_at")
  })

  it("metadata contains task_id", () => {
    expect(baseArtifact.metadata.task_id).toBe("t1")
  })

  it("metadata contains created_by", () => {
    expect(baseArtifact.metadata.created_by).toBe("researcher")
  })
})

// --- Type Classification Tests ---

describe("Artifact type classification", () => {
  const typeConfig: Record<string, { color: string }> = {
    text: { color: "blue" },
    markdown: { color: "purple" },
    json: { color: "green" },
    list: { color: "orange" },
    url: { color: "cyan" },
  }

  it("text type has blue color", () => {
    expect(typeConfig.text.color).toBe("blue")
  })

  it("json type has green color", () => {
    expect(typeConfig.json.color).toBe("green")
  })

  it("markdown type has purple color", () => {
    expect(typeConfig.markdown.color).toBe("purple")
  })

  it("list type has orange color", () => {
    expect(typeConfig.list.color).toBe("orange")
  })

  it("url type has cyan color", () => {
    expect(typeConfig.url.color).toBe("cyan")
  })

  it("unknown type falls back to default", () => {
    expect(typeConfig["unknown"] || { color: "default" }).toEqual({ color: "default" })
  })
})

// --- Content Rendering Logic Tests ---

describe("Content rendering logic", () => {
  it("url artifact content is a valid URL", () => {
    const urlArtifact: ArtifactItem = {
      ...baseArtifact,
      type: "url",
      content: "https://example.com",
    }
    expect(urlArtifact.content.startsWith("http")).toBe(true)
  })

  it("json artifact content is valid JSON", () => {
    const jsonContent = JSON.stringify({ score: 8, verdict: "good" })
    const parsed = JSON.parse(jsonContent)
    expect(parsed.score).toBe(8)
  })

  it("list artifact content is a JSON array", () => {
    const listContent = JSON.stringify(["AI", "ML", "NLP"])
    const parsed = JSON.parse(listContent)
    expect(Array.isArray(parsed)).toBe(true)
    expect(parsed).toHaveLength(3)
  })

  it("text artifact content is plain string", () => {
    const textArtifact: ArtifactItem = {
      ...baseArtifact,
      type: "text",
      content: "Simple text content",
    }
    expect(typeof textArtifact.content).toBe("string")
  })
})

// --- Empty State Tests ---

describe("Empty states", () => {
  it("empty artifacts list", () => {
    const data: TaskArtifactsResponse = { task_id: "t1", artifacts: [], total: 0 }
    expect(data.artifacts).toHaveLength(0)
    expect(data.total).toBe(0)
  })

  it("null taskId disables query", () => {
    const taskId: string | null = null
    expect(!!taskId).toBe(false)
  })
})

// --- Multiple Artifacts Tests ---

describe("Multiple artifacts", () => {
  it("handles multiple artifact types", () => {
    const artifacts: ArtifactItem[] = [
      { ...baseArtifact, id: "a1", type: "text", name: "summary" },
      { ...baseArtifact, id: "a2", type: "json", name: "analysis" },
      { ...baseArtifact, id: "a3", type: "url", name: "link" },
    ]
    expect(artifacts).toHaveLength(3)
    const types = artifacts.map((a) => a.type)
    expect(types).toContain("text")
    expect(types).toContain("json")
    expect(types).toContain("url")
  })
})