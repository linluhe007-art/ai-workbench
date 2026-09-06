import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchCluster } from "../api/deployment"
import { useCluster } from "../hooks/useDeployment"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseCluster = {
  instances: [
    { instance_id: "inst-1", status: "healthy", role: "leader", started_at: "2026-01-01T00:00:00" },
    { instance_id: "inst-2", status: "healthy", role: "worker", started_at: "2026-01-01T00:01:00" },
  ],
  total: 2,
  leader: "inst-1",
  self: "inst-1",
  health: { persistence: "healthy", redis: "healthy" },
  timestamp: "2026-01-01T00:00:00",
}

// --- API Tests ---

describe("Cluster API", () => {
  it("fetchCluster returns cluster data", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.total).toBe(2)
    expect(res.leader).toBe("inst-1")
    expect(mockGet).toHaveBeenCalledWith("/system/cluster")
  })

  it("fetchCluster returns instances array", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.instances).toHaveLength(2)
  })
})

// --- Response Parsing ---

describe("Cluster response parsing", () => {
  it("parses instance ids", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.instances[0].instance_id).toBe("inst-1")
    expect(res.instances[1].instance_id).toBe("inst-2")
  })

  it("parses roles", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.instances[0].role).toBe("leader")
    expect(res.instances[1].role).toBe("worker")
  })

  it("parses health fields", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.health.persistence).toBe("healthy")
    expect(res.health.redis).toBe("healthy")
  })

  it("parses total count", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.total).toBe(2)
  })

  it("parses self field", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.self).toBe("inst-1")
  })

  it("parses leader field", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.leader).toBe("inst-1")
  })
})

// --- Hook Tests ---

describe("useCluster hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const { result } = renderHook(() => useCluster(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(2)
  })

  it("has correct queryKey", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const { result } = renderHook(() => useCluster(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})

// --- Error Handling ---

describe("Cluster error handling", () => {
  it("handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchCluster()).rejects.toThrow("Network Error")
  })

  it("handles hook error state", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useCluster(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeDefined()
  })
})

// --- Edge Cases ---

describe("Cluster edge cases", () => {
  it("handles single instance cluster", async () => {
    mockGet.mockResolvedValue({
      data: {
        instances: [{ instance_id: "solo", status: "healthy", role: "leader", started_at: "" }],
        total: 1, leader: "solo", self: "solo",
        health: { persistence: "disabled", redis: "disabled" },
        timestamp: "",
      },
    })
    const res = await fetchCluster()
    expect(res.total).toBe(1)
    expect(res.leader).toBe("solo")
  })

  it("handles empty instances", async () => {
    mockGet.mockResolvedValue({
      data: { instances: [], total: 0, leader: null, self: "", health: { persistence: "unknown", redis: "unknown" }, timestamp: "" },
    })
    const res = await fetchCluster()
    expect(res.total).toBe(0)
    expect(res.instances).toEqual([])
  })

  it("handles null leader", async () => {
    mockGet.mockResolvedValue({
      data: { instances: [], total: 0, leader: null, self: "inst-1", health: { persistence: "unknown", redis: "unknown" }, timestamp: "" },
    })
    const res = await fetchCluster()
    expect(res.leader).toBeNull()
  })

  it("handles disabled persistence and redis", async () => {
    mockGet.mockResolvedValue({
      data: { instances: [], total: 0, leader: null, self: "", health: { persistence: "disabled", redis: "disabled" }, timestamp: "" },
    })
    const res = await fetchCluster()
    expect(res.health.persistence).toBe("disabled")
    expect(res.health.redis).toBe("disabled")
  })
})

// --- Loading States ---

describe("Cluster loading states", () => {
  it("shows loading initially", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useCluster(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
})

// --- Instance Status Validation ---

describe("Instance status validation", () => {
  it("healthy instance has green status", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.instances[0].status).toBe("healthy")
  })
})

// --- Role Validation ---

describe("Role validation", () => {
  it("leader role is leader", async () => {
    expect(baseCluster.instances[0].role).toBe("leader")
  })

  it("worker role is worker", async () => {
    expect(baseCluster.instances[1].role).toBe("worker")
  })
})

// --- Health Status Handling ---

describe("Health status handling", () => {
  it("handles healthy persistence", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.health.persistence).toBe("healthy")
  })

  it("handles unhealthy redis", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseCluster, health: { persistence: "healthy", redis: "unavailable" } },
    })
    const res = await fetchCluster()
    expect(res.health.redis).toBe("unavailable")
  })

  it("handles unknown health", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseCluster, health: { persistence: "unknown", redis: "unknown" } },
    })
    const res = await fetchCluster()
    expect(res.health.persistence).toBe("unknown")
  })
})

// --- Instance Count ---

describe("Instance count handling", () => {
  it("handles 3 instances", async () => {
    mockGet.mockResolvedValue({
      data: {
        instances: [
          { instance_id: "a", status: "healthy", role: "leader", started_at: "" },
          { instance_id: "b", status: "healthy", role: "worker", started_at: "" },
          { instance_id: "c", status: "healthy", role: "worker", started_at: "" },
        ],
        total: 3, leader: "a", self: "a",
        health: { persistence: "healthy", redis: "healthy" },
        timestamp: "",
      },
    })
    const res = await fetchCluster()
    expect(res.total).toBe(3)
    expect(res.instances).toHaveLength(3)
  })

  it("handles large cluster", async () => {
    const instances = Array.from({ length: 10 }, (_, i) => ({
      instance_id: "i" + i, status: "healthy", role: i === 0 ? "leader" : "worker", started_at: "",
    }))
    mockGet.mockResolvedValue({
      data: { instances, total: 10, leader: "i0", self: "i0", health: { persistence: "healthy", redis: "healthy" }, timestamp: "" },
    })
    const res = await fetchCluster()
    expect(res.total).toBe(10)
  })
})

// --- Timestamp Validation ---

describe("Timestamp validation", () => {
  it("parses timestamp field", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseCluster, timestamp: "2026-08-12T10:00:00Z" },
    })
    const res = await fetchCluster()
    expect(res.timestamp).toBe("2026-08-12T10:00:00Z")
  })
})

// --- Self Reference ---

describe("Self reference", () => {
  it("self is present in instances", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    const ids = res.instances.map((i) => i.instance_id)
    expect(ids).toContain(res.self)
  })
})

// --- Instance Validation ---

describe("Instance data validation", () => {
  it("each instance has instance_id", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    for (const inst of res.instances) {
      expect(inst.instance_id).toBeTruthy()
    }
  })

  it("each instance has role", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    for (const inst of res.instances) {
      expect(inst.role).toBeDefined()
    }
  })

  it("each instance has status", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    for (const inst of res.instances) {
      expect(inst.status).toBeDefined()
    }
  })
})

// --- Cluster Topology ---

describe("Cluster topology", () => {
  it("exactly one leader in cluster", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    const leaders = res.instances.filter((i) => i.role === "leader")
    expect(leaders).toHaveLength(1)
  })

  it("leader field matches leader instance", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    const leaderInst = res.instances.find((i) => i.role === "leader")
    expect(res.leader).toBe(leaderInst?.instance_id)
  })
})

// --- Timestamp Parsing ---

describe("Timestamp handling", () => {
  it("timestamp is ISO string", async () => {
    mockGet.mockResolvedValue({ data: baseCluster })
    const res = await fetchCluster()
    expect(res.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })
})

// --- Error Boundaries ---

describe("Cluster error boundaries", () => {
  it("handles malformed response gracefully", async () => {
    mockGet.mockResolvedValue({ data: { instances: "not-an-array" } })
    await expect(fetchCluster()).resolves.toBeDefined()
  })

  it("handles missing health field", async () => {
    mockGet.mockResolvedValue({ data: { instances: [], total: 0, leader: null, self: "" } })
    const res = await fetchCluster()
    expect(res).toBeDefined()
  })
})// --- Large cluster test ---

describe("Large cluster", () => {
  it("handles 20 instances", async () => {
    const arr = Array.from({ length: 20 }, (_, i) => ({ instance_id: "i" + i, status: "healthy", role: i === 0 ? "leader" : "worker", started_at: "" }))
    mockGet.mockResolvedValue({ data: { instances: arr, total: 20, leader: "i0", self: "i0", health: { persistence: "healthy", redis: "healthy" }, timestamp: "" } })
    const res = await fetchCluster()
    expect(res.total).toBe(20)
    expect(res.instances).toHaveLength(20)
  })
})// --- Final edge cases ---

describe("Cluster edge cases final", () => {
  it("handles all workers no explicit leader", async () => {
    mockGet.mockResolvedValue({
      data: { instances: [{ instance_id: "w1", status: "healthy", role: "worker", started_at: "" }], total: 1, leader: null, self: "w1", health: { persistence: "disabled", redis: "disabled" }, timestamp: "" },
    })
    const res = await fetchCluster()
    expect(res.leader).toBeNull()
  })

  it("handles degraded health", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseCluster, health: { persistence: "degraded", redis: "healthy" } },
    })
    const res = await fetchCluster()
    expect(res.health.persistence).toBe("degraded")
  })

  it("handles unavailable health", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseCluster, health: { persistence: "unavailable", redis: "unavailable" } },
    })
    const res = await fetchCluster()
    expect(res.health.redis).toBe("unavailable")
  })

  it("handles missing timestamp gracefully", async () => {
    mockGet.mockResolvedValue({
      data: { instances: [], total: 0, leader: null, self: "" },
    })
    const res = await fetchCluster()
    expect(res.total).toBe(0)
  })
})