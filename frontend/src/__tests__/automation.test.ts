import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  fetchAutomations,
  createAutomation,
  fetchAutomation,
  runAutomation,
  updateAutomationStatus,
  deleteAutomation,
  fetchAutomationLogs,
} from "../api/automation"
import { useAutomations, useAutomation, useAutomationLogs } from "../hooks/useAutomation"

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

const baseAutomation = {
  id: "auto-1",
  name: "Daily Report",
  description: "Generate daily report at 6pm",
  trigger: { trigger_type: "schedule", cron_expression: "0 18 * * *", event_name: "", webhook_url: "", metadata: {} },
  action: { type: "create_task", params: {} },
  status: "active",
  last_run_at: "2026-01-01T18:00:00",
  run_count: 5,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T18:00:00",
}

const baseListResponse = {
  success: true,
  automations: [baseAutomation],
  total: 1,
}

// ===== API Tests =====

describe("Automation API", () => {
  it("fetchAutomations returns automation list", async () => {
    mockGet.mockResolvedValue({ data: baseListResponse })
    const res = await fetchAutomations()
    expect(res.automations).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/automation")
  })

  it("fetchAutomations returns empty list", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automations: [], total: 0 } })
    const res = await fetchAutomations()
    expect(res.automations).toHaveLength(0)
    expect(res.total).toBe(0)
  })

  it("createAutomation sends create request", async () => {
    mockPost.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    const res = await createAutomation({ name: "Test", trigger_type: "manual" })
    expect(res.success).toBe(true)
    expect(res.automation.name).toBe("Daily Report")
    expect(mockPost).toHaveBeenCalledWith("/automation", { name: "Test", trigger_type: "manual" })
  })

  it("createAutomation includes all fields", async () => {
    mockPost.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    const req = {
      name: "Full",
      description: "desc",
      trigger_type: "schedule",
      cron_expression: "0 9 * * *",
      action_type: "notify",
      action_params: { channel: "slack" },
    }
    await createAutomation(req)
    expect(mockPost).toHaveBeenCalledWith("/automation", req)
  })

  it("fetchAutomation fetches single automation", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    const res = await fetchAutomation("auto-1")
    expect(res.automation.id).toBe("auto-1")
    expect(mockGet).toHaveBeenCalledWith("/automation/auto-1")
  })

  it("runAutomation triggers execution", async () => {
    mockPost.mockResolvedValue({ data: { success: true, log: null } })
    const res = await runAutomation("auto-1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/automation/auto-1/run")
  })

  it("updateAutomationStatus changes status", async () => {
    mockPut.mockResolvedValue({ data: { success: true } })
    const res = await updateAutomationStatus("auto-1", "paused")
    expect(res.success).toBe(true)
    expect(mockPut).toHaveBeenCalled()
  })

  it("deleteAutomation removes automation", async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const res = await deleteAutomation("auto-1")
    expect(res.success).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/automation/auto-1")
  })

  it("fetchAutomationLogs returns logs", async () => {
    const logsData = {
      success: true,
      logs: [
        {
          id: "log-1",
          automation_id: "auto-1",
          status: "completed",
          result: { output: "ok" },
          error: "",
          started_at: "2026-01-01T18:00:00",
          finished_at: "2026-01-01T18:00:05",
          created_at: "2026-01-01T18:00:00",
        },
      ],
      total: 1,
    }
    mockGet.mockResolvedValue({ data: logsData })
    const res = await fetchAutomationLogs("auto-1", 20)
    expect(res.logs).toHaveLength(1)
    expect(res.logs[0].status).toBe("completed")
    expect(mockGet).toHaveBeenCalledWith("/automation/auto-1/logs?limit=20")
  })

  it("fetchAutomationLogs uses default limit", async () => {
    mockGet.mockResolvedValue({ data: { success: true, logs: [], total: 0 } })
    await fetchAutomationLogs("auto-1")
    expect(mockGet).toHaveBeenCalledWith("/automation/auto-1/logs?limit=50")
  })
})

// ===== Response Parsing =====

describe("Automation Response Parsing", () => {
  it("parses automation with trigger fields", async () => {
    mockGet.mockResolvedValue({ data: baseListResponse })
    const res = await fetchAutomations()
    expect(res.automations[0].trigger.trigger_type).toBe("schedule")
    expect(res.automations[0].trigger.cron_expression).toBe("0 18 * * *")
  })

  it("parses automation with status", async () => {
    mockGet.mockResolvedValue({ data: baseListResponse })
    const res = await fetchAutomations()
    expect(res.automations[0].status).toBe("active")
    expect(res.automations[0].run_count).toBe(5)
  })
})

// ===== Hook Tests =====

describe("useAutomations hook", () => {
  it("returns automation list data", async () => {
    mockGet.mockResolvedValue({ data: baseListResponse })
    const { result } = renderHook(() => useAutomations(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.automations).toHaveLength(1)
  })

  it("handles empty automation list", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automations: [], total: 0 } })
    const { result } = renderHook(() => useAutomations(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.automations).toHaveLength(0)
  })
})

describe("useAutomation hook", () => {
  it("returns single automation when enabled", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    const { result } = renderHook(() => useAutomation("auto-1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.automation.id).toBe("auto-1")
  })

  it("does not fetch when id is null", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    renderHook(() => useAutomation(null), { wrapper })
    await new Promise((r) => setTimeout(r, 100))
    expect(mockGet).not.toHaveBeenCalled()
  })
})

describe("useAutomationLogs hook", () => {
  it("returns logs data", async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        logs: [{ id: "log-1", automation_id: "auto-1", status: "completed", result: {}, error: "", started_at: "", finished_at: "", created_at: "" }],
        total: 1,
      },
    })
    const { result } = renderHook(() => useAutomationLogs("auto-1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.logs).toHaveLength(1)
  })

  it("does not fetch when id is null", async () => {
    mockGet.mockResolvedValue({ data: { success: true, logs: [], total: 0 } })
    renderHook(() => useAutomationLogs(null), { wrapper })
    await new Promise((r) => setTimeout(r, 100))
    expect(mockGet).not.toHaveBeenCalled()
  })
})

// ===== Query Key Tests =====

describe("Automation Query Keys", () => {
  it("useAutomations uses correct query key", async () => {
    mockGet.mockResolvedValue({ data: baseListResponse })
    const { result } = renderHook(() => useAutomations(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockGet).toHaveBeenCalledWith("/automation")
  })

  it("useAutomation uses id in query key", async () => {
    mockGet.mockResolvedValue({ data: { success: true, automation: baseAutomation } })
    renderHook(() => useAutomation("auto-xyz"), { wrapper })
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
  })
})
