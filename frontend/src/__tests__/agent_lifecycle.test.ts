import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  fetchAgentRegistry,
  registerAgent,
  sendHeartbeat,
  disableAgent,
  enableAgent,
  fetchAgentRuntime,
} from "../api/agentLifecycle"
import {
  useAgentRegistry,
  useAgentRuntime,
} from "../hooks/useAgentLifecycle"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseRegistryResponse = {
  agents: [
    {
      agent_id: "mock",
      name: "MockAgent",
      capabilities: ["research", "analysis"],
      enabled: true,
      alive: true,
      last_heartbeat: "2026-08-12T10:00:00Z",
      lifecycle_state: "ready",
      active_tasks: 1,
      max_concurrent: 3,
    },
    {
      agent_id: "researcher",
      name: "Researcher",
      capabilities: ["research"],
      enabled: true,
      alive: true,
      last_heartbeat: "2026-08-12T09:58:00Z",
      lifecycle_state: "idle",
      active_tasks: 0,
      max_concurrent: 3,
    },
  ],
  total: 2,
}

// --- API Tests ---

describe("Agent Lifecycle API", () => {
  it("fetchAgentRegistry returns agents", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const res = await fetchAgentRegistry()
    expect(res.total).toBe(2)
    expect(res.agents).toHaveLength(2)
    expect(mockGet).toHaveBeenCalledWith("/agents/registry")
  })

  it("registerAgent sends correct payload", async () => {
    mockPost.mockResolvedValue({ data: { success: true, agent_id: "new1" } })
    const res = await registerAgent("new1", ["research"])
    expect(res.success).toBe(true)
    expect(res.agent_id).toBe("new1")
    expect(mockPost).toHaveBeenCalledWith("/agents/register", {
      agent_id: "new1",
      capabilities: ["research"],
    })
  })

  it("sendHeartbeat sends request", async () => {
    mockPost.mockResolvedValue({ data: { agent_id: "a1", alive: true } })
    const res = await sendHeartbeat("a1")
    expect(res.alive).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/agents/a1/heartbeat")
  })

  it("disableAgent sends request", async () => {
    mockPost.mockResolvedValue({ data: { success: true, enabled: false } })
    const res = await disableAgent("a1")
    expect(res.enabled).toBe(false)
    expect(mockPost).toHaveBeenCalledWith("/agents/a1/disable")
  })

  it("enableAgent sends request", async () => {
    mockPost.mockResolvedValue({ data: { success: true, enabled: true } })
    const res = await enableAgent("a1")
    expect(res.enabled).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/agents/a1/enable")
  })

  it("fetchAgentRuntime returns runtime data", async () => {
    mockGet.mockResolvedValue({
      data: {
        agent_id: "a1",
        name: "Test",
        state: "idle",
        task: "",
        started_at: null,
        completed_at: null,
        error: "",
        load: { active_tasks: 0, max_concurrent: 3 },
        capabilities: ["research"],
      },
    })
    const res = await fetchAgentRuntime("a1")
    expect(res.agent_id).toBe("a1")
    expect(res.state).toBe("idle")
    expect(mockGet).toHaveBeenCalledWith("/agents/a1/runtime")
  })
})

// --- Response Parsing ---

describe("Agent registry response parsing", () => {
  it("parses agent capabilities", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].capabilities).toEqual(["research", "analysis"])
    expect(res.agents[1].capabilities).toEqual(["research"])
  })

  it("parses lifecycle state", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].lifecycle_state).toBe("ready")
    expect(res.agents[1].lifecycle_state).toBe("idle")
  })

  it("parses load info", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].active_tasks).toBe(1)
    expect(res.agents[0].max_concurrent).toBe(3)
  })

  it("parses enabled flag", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].enabled).toBe(true)
  })
})

// --- Hook Tests ---

describe("useAgentRegistry hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const { result } = renderHook(() => useAgentRegistry(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(2)
  })

  it("has correct queryKey", async () => {
    mockGet.mockResolvedValue({ data: baseRegistryResponse })
    const { result } = renderHook(() => useAgentRegistry(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})

describe("useAgentRuntime hook", () => {
  it("fetches runtime for specific agent", async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: "a1", name: "A", state: "idle", task: "", started_at: null, completed_at: null, error: "", load: { active_tasks: 0, max_concurrent: 3 }, capabilities: [] },
    })
    const { result } = renderHook(() => useAgentRuntime("a1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.state).toBe("idle")
  })

  it("does not fetch when agentId is empty", () => {
    const { result } = renderHook(() => useAgentRuntime(""), { wrapper })
    expect(result.current.isLoading).toBe(false)
  })
})

// --- Error Handling ---

describe("Agent lifecycle error handling", () => {
  it("fetchAgentRegistry handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchAgentRegistry()).rejects.toThrow("Network Error")
  })

  it("registerAgent handles network error", async () => {
    mockPost.mockRejectedValue(new Error("Failed"))
    await expect(registerAgent("x", [])).rejects.toThrow("Failed")
  })

  it("sendHeartbeat handles 404", async () => {
    mockPost.mockRejectedValue({ response: { status: 404 }, message: "Not found" })
    await expect(sendHeartbeat("ghost")).rejects.toBeDefined()
  })

  it("disableAgent handles network error", async () => {
    mockPost.mockRejectedValue(new Error("Service Unavailable"))
    await expect(disableAgent("a1")).rejects.toThrow("Service Unavailable")
  })

  it("enableAgent handles network error", async () => {
    mockPost.mockRejectedValue(new Error("Timeout"))
    await expect(enableAgent("a1")).rejects.toThrow("Timeout")
  })

  it("fetchAgentRuntime handles 404", async () => {
    mockGet.mockRejectedValue({ response: { status: 404 }, message: "Not found" })
    await expect(fetchAgentRuntime("ghost")).rejects.toBeDefined()
  })
})

// --- Edge Cases ---

describe("Agent lifecycle edge cases", () => {
  it("handles empty registry", async () => {
    mockGet.mockResolvedValue({ data: { agents: [], total: 0 } })
    const res = await fetchAgentRegistry()
    expect(res.agents).toHaveLength(0)
    expect(res.total).toBe(0)
  })

  it("handles agent with no capabilities", async () => {
    mockGet.mockResolvedValue({
      data: {
        agents: [{ agent_id: "bare", name: "", capabilities: [], enabled: true, alive: true, last_heartbeat: null, lifecycle_state: "unknown", active_tasks: 0, max_concurrent: 3 }],
        total: 1,
      },
    })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].capabilities).toEqual([])
  })

  it("handles agent with zero load", async () => {
    mockGet.mockResolvedValue({
      data: {
        agents: [{ agent_id: "idle1", name: "Idle", capabilities: ["research"], enabled: true, alive: true, last_heartbeat: null, lifecycle_state: "ready", active_tasks: 0, max_concurrent: 3 }],
        total: 1,
      },
    })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].active_tasks).toBe(0)
  })

  it("handles agent with many capabilities", async () => {
    mockGet.mockResolvedValue({
      data: {
        agents: [{ agent_id: "omni", name: "Omni", capabilities: ["research", "analysis", "writing", "coding", "testing"], enabled: true, alive: true, last_heartbeat: null, lifecycle_state: "ready", active_tasks: 2, max_concurrent: 5 }],
        total: 1,
      },
    })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].capabilities).toHaveLength(5)
  })
})

// --- Loading/Error States ---

describe("Agent lifecycle loading states", () => {
  it("shows loading initially for registry", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useAgentRegistry(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("shows loading initially for runtime", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useAgentRuntime("a1"), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state in hook", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useAgentRegistry(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeDefined()
  })
})

// --- Disabled Agent Handling ---

describe("Disabled agent handling", () => {
  it("parses disabled agent", async () => {
    mockGet.mockResolvedValue({
      data: {
        agents: [{ agent_id: "off", name: "Offline", capabilities: ["research"], enabled: false, alive: true, last_heartbeat: null, lifecycle_state: "stopped", active_tasks: 0, max_concurrent: 3 }],
        total: 1,
      },
    })
    const res = await fetchAgentRegistry()
    expect(res.agents[0].enabled).toBe(false)
    expect(res.agents[0].lifecycle_state).toBe("stopped")
  })

  it("handles enable/disable toggle via API", async () => {
    mockPost.mockResolvedValue({ data: { success: true, agent_id: "a1", enabled: true } })
    const enableRes = await enableAgent("a1")
    expect(enableRes.enabled).toBe(true)

    mockPost.mockResolvedValue({ data: { success: true, agent_id: "a1", enabled: false } })
    const disableRes = await disableAgent("a1")
    expect(disableRes.enabled).toBe(false)
  })
})

// --- Runtime State Values ---

describe("Runtime state values", () => {
  it("handles idle state", async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: "a1", name: "A", state: "idle", task: "", started_at: null, completed_at: null, error: "", load: { active_tasks: 0, max_concurrent: 3 }, capabilities: [] },
    })
    const res = await fetchAgentRuntime("a1")
    expect(res.state).toBe("idle")
  })

  it("handles running state", async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: "a1", name: "A", state: "running", task: "test", started_at: "2026-08-12T10:00:00Z", completed_at: null, error: "", load: { active_tasks: 1, max_concurrent: 3 }, capabilities: [] },
    })
    const res = await fetchAgentRuntime("a1")
    expect(res.state).toBe("running")
  })

  it("handles failed state", async () => {
    mockGet.mockResolvedValue({
      data: { agent_id: "a1", name: "A", state: "failed", task: "", started_at: null, completed_at: "2026-08-12T10:00:00Z", error: "timeout", load: { active_tasks: 0, max_concurrent: 3 }, capabilities: [] },
    })
    const res = await fetchAgentRuntime("a1")
    expect(res.state).toBe("failed")
    expect(res.error).toBe("timeout")
  })
})