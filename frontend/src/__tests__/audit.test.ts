import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import {
  fetchAuditRecords,
  fetchTaskAuditTrail,
  fetchAgentAudit,
  fetchAuditStats,
  type AuditRecord,
  type AuditQueryResponse,
  type TaskAuditTrailResponse,
} from "../api/audit"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

const baseRecord: AuditRecord = {
  id: "audit-1",
  timestamp: "2026-08-12T10:00:00Z",
  actor: "system",
  action: "create_task",
  resource_type: "task",
  resource_id: "task-1",
  task_id: "task-1",
  request_id: null,
  before: {},
  after: {},
  metadata: {},
}

const baseResponse: AuditQueryResponse = {
  items: [baseRecord],
  total: 1,
  limit: 50,
  offset: 0,
}

// =============================================================================
// Audit API Tests
// =============================================================================

describe("fetchAuditRecords", () => {
  it("calls GET /audit with no params", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchAuditRecords()
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: {} })
  })

  it("passes task_id param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ task_id: "task-1" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { task_id: "task-1" } })
  })

  it("passes actor param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ actor: "researcher" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { actor: "researcher" } })
  })

  it("passes action param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ action: "task_completed" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { action: "task_completed" } })
  })

  it("passes resource_type param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ resource_type: "artifact" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { resource_type: "artifact" } })
  })

  it("passes resource_id param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ resource_id: "res-1" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { resource_id: "res-1" } })
  })

  it("passes request_id param", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ request_id: "req-1" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { request_id: "req-1" } })
  })

  it("passes limit and offset", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ limit: 20, offset: 10 })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: { limit: 20, offset: 10 } })
  })

  it("excludes null/empty params", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ task_id: null, actor: "" })
    expect(mockGet).toHaveBeenCalledWith("/audit", { params: {} })
  })

  it("passes combined filters", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    await fetchAuditRecords({ task_id: "t1", actor: "system", action: "create_task", limit: 10 })
    expect(mockGet).toHaveBeenCalledWith("/audit", {
      params: { task_id: "t1", actor: "system", action: "create_task", limit: 10 },
    })
  })

  it("handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchAuditRecords()).rejects.toThrow("Network Error")
  })

  it("returns empty result", async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })
    const res = await fetchAuditRecords()
    expect(res.total).toBe(0)
    expect(res.items).toHaveLength(0)
  })
})

// =============================================================================
// Task Audit Trail Tests
// =============================================================================

describe("fetchTaskAuditTrail", () => {
  it("calls GET /tasks/{id}/audit", async () => {
    const trailResp: TaskAuditTrailResponse = {
      task_id: "task-1",
      audit_trail: [baseRecord],
      total: 1,
      exists: true,
    }
    mockGet.mockResolvedValue({ data: trailResp })
    const res = await fetchTaskAuditTrail("task-1")
    expect(res.task_id).toBe("task-1")
    expect(res.exists).toBe(true)
    expect(res.audit_trail).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/tasks/task-1/audit")
  })

  it("returns empty trail for non-existent task", async () => {
    const trailResp: TaskAuditTrailResponse = {
      task_id: "nonexistent",
      audit_trail: [],
      total: 0,
      exists: false,
    }
    mockGet.mockResolvedValue({ data: trailResp })
    const res = await fetchTaskAuditTrail("nonexistent")
    expect(res.exists).toBe(false)
    expect(res.audit_trail).toHaveLength(0)
  })

  it("handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchTaskAuditTrail("task-1")).rejects.toThrow("Network Error")
  })
})

// =============================================================================
// Agent Audit Tests
// =============================================================================

describe("fetchAgentAudit", () => {
  it("calls GET /agents/{id}/audit", async () => {
    const agentResp = { agent_id: "researcher", items: [baseRecord], total: 1 }
    mockGet.mockResolvedValue({ data: agentResp })
    const res = await fetchAgentAudit("researcher")
    expect(res.agent_id).toBe("researcher")
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/agents/researcher/audit", { params: { limit: 100 } })
  })

  it("passes custom limit", async () => {
    const agentResp = { agent_id: "researcher", items: [], total: 0 }
    mockGet.mockResolvedValue({ data: agentResp })
    await fetchAgentAudit("researcher", 50)
    expect(mockGet).toHaveBeenCalledWith("/agents/researcher/audit", { params: { limit: 50 } })
  })

  it("handles empty response", async () => {
    const agentResp = { agent_id: "unknown", items: [], total: 0 }
    mockGet.mockResolvedValue({ data: agentResp })
    const res = await fetchAgentAudit("unknown")
    expect(res.items).toHaveLength(0)
    expect(res.total).toBe(0)
  })
})

// =============================================================================
// Audit Stats Tests
// =============================================================================

describe("fetchAuditStats", () => {
  it("calls GET /audit/stats", async () => {
    mockGet.mockResolvedValue({ data: { total_records: 42, status: "active" } })
    const res = await fetchAuditStats()
    expect(res.total_records).toBe(42)
    expect(res.status).toBe("active")
    expect(mockGet).toHaveBeenCalledWith("/audit/stats")
  })
})

// =============================================================================
// AuditRecord Type Tests
// =============================================================================

describe("AuditRecord type", () => {
  it("has all required fields", () => {
    const record: AuditRecord = baseRecord
    expect(record.id).toBe("audit-1")
    expect(record.actor).toBe("system")
    expect(record.action).toBe("create_task")
    expect(record.resource_type).toBe("task")
    expect(record.resource_id).toBe("task-1")
    expect(record.task_id).toBe("task-1")
    expect(record.request_id).toBeNull()
    expect(record.before).toEqual({})
    expect(record.after).toEqual({})
    expect(record.metadata).toEqual({})
  })

  it("supports full metadata", () => {
    const record: AuditRecord = {
      id: "r-2",
      timestamp: "2026-08-12T11:00:00Z",
      actor: "writer",
      action: "artifact_created",
      resource_type: "artifact",
      resource_id: "art-1",
      task_id: "task-1",
      request_id: "req-1",
      before: { status: "pending" },
      after: { status: "created", name: "report.md" },
      metadata: { type: "markdown", size: 1024 },
    }
    expect(record.metadata.type).toBe("markdown")
    expect(record.after.status).toBe("created")
  })

  it("supports nullable task_id and request_id", () => {
    const record: AuditRecord = {
      id: "r-null",
      timestamp: "2026-08-12T12:00:00Z",
      actor: "system",
      action: "config_change",
      resource_type: "system",
      resource_id: "settings",
      task_id: null,
      request_id: null,
      before: {},
      after: {},
      metadata: {},
    }
    expect(record.task_id).toBeNull()
    expect(record.request_id).toBeNull()
  })
})

// =============================================================================
// Query Response Type Tests
// =============================================================================

describe("AuditQueryResponse type", () => {
  it("validates response structure", () => {
    const response: AuditQueryResponse = {
      items: [baseRecord],
      total: 1,
      limit: 50,
      offset: 0,
    }
    expect(response.items).toHaveLength(1)
    expect(response.total).toBe(1)
    expect(response.limit).toBe(50)
    expect(response.offset).toBe(0)
  })

  it("handles paginated response", () => {
    const response: AuditQueryResponse = {
      items: [baseRecord, { ...baseRecord, id: "audit-2" }],
      total: 100,
      limit: 20,
      offset: 40,
    }
    expect(response.items).toHaveLength(2)
    expect(response.total).toBe(100)
    expect(response.limit).toBe(20)
    expect(response.offset).toBe(40)
  })
})

// =============================================================================
// AuditQueryParams Tests
// =============================================================================

describe("AuditQueryParams", () => {
  it("allows all optional filters", () => {
    const params = {
      task_id: "t1",
      actor: "system",
      action: "create_task",
      resource_type: "task",
      resource_id: "t1",
      request_id: "req-1",
      limit: 10,
      offset: 0,
    }
    expect(params.task_id).toBe("t1")
    expect(params.limit).toBe(10)
  })

  it("allows empty params", () => {
    const params = {}
    expect(Object.keys(params)).toHaveLength(0)
  })
})